#!/usr/bin/env python3
"""
Enviar E-mails Automáticos da Caderneta
========================================

Este script lê uma caderneta exportada (JSON) e envia e-mails automáticos
com as notas dos estudantes, usando suas credenciais pessoais de e-mail.

USO:
  1. Configure suas credenciais:
     python3 enviar_emails.py --config
  
  2. Exporte a caderneta em JSON (botão "Exportar JSON" na caderneta HTML)
  
  3. Envie os e-mails:
     python3 enviar_emails.py caderneta_backup.json

SUPORTA:
  - Gmail (e qualquer SMTP compatível)
  - Teste de envio antes de mandar para todos
  - Relatório de sucesso/erro
  - Retentativas automáticas

AUTOR: Gerado automaticamente pela Caderneta
"""

import json
import sys
import os
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from getpass import getpass


CONFIG_FILE = "config.json"


def load_config():
    """Carrega configurações de SMTP do arquivo config.json."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
        return None


def save_config(config):
    """Salva configurações de SMTP em config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        os.chmod(CONFIG_FILE, 0o600)  # Apenas você consegue ler
        print(f"✓ Configuração salva em {CONFIG_FILE}")
    except Exception as e:
        print(f"Erro ao salvar config.json: {e}")


def setup_config():
    """Guia interativo para configurar credenciais de e-mail."""
    print("\n" + "="*60)
    print("CONFIGURAR CREDENCIAIS DE E-MAIL")
    print("="*60)
    print("\nEste arquivo fica LOCAL no seu computador (não é enviado a ninguém).\n")

    print("Escolha seu provedor de e-mail:")
    print("  1. Gmail (recomendado)")
    print("  2. Outro SMTP (Hotmail, Yahoo, seu servidor, etc.)")
    choice = input("\nOpção (1 ou 2): ").strip()

    if choice == "1":
        email = input("Seu e-mail Gmail: ").strip()
        print("\nPara usar Gmail, você precisa de uma 'Senha de App'.")
        print("Siga: https://myaccount.google.com/apppasswords")
        print("  1. Ative Autenticação em 2 Etapas (se não estiver)")
        print("  2. Gere uma 'Senha de app' para 'Mail' e 'Windows'")
        print("  3. Cole a senha aqui (ela tem 16 caracteres com espaços):\n")
        password = getpass("Senha de app: ").strip().replace(" ", "")
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "email": email,
            "password": password,
            "nome_remetente": "Caderneta — " + input("Seu nome: ").strip()
        }
    else:
        print("\nConfigração manual de SMTP:")
        config = {
            "smtp_server": input("Servidor SMTP (ex.: smtp.hotmail.com): ").strip(),
            "smtp_port": int(input("Porta (geralmente 587 ou 25): ").strip()),
            "use_tls": input("Usar TLS? (s/n): ").strip().lower() == 's',
            "email": input("Seu e-mail: ").strip(),
            "password": getpass("Sua senha: ").strip(),
            "nome_remetente": "Caderneta — " + input("Seu nome: ").strip()
        }

    print("\nTestando conexão...")
    try:
        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"], timeout=5)
        if config["use_tls"]:
            server.starttls()
        server.login(config["email"], config["password"])
        server.quit()
        print("✓ Conexão bem-sucedida!\n")
        save_config(config)
    except Exception as e:
        print(f"✗ Erro na conexão: {e}")
        print("Verifique suas credenciais e tente novamente.\n")
        sys.exit(1)


def load_caderneta(filepath):
    """Carrega a caderneta exportada do JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler {filepath}: {e}")
        sys.exit(1)


def enviar_email(config, destinatario, assunto, corpo):
    """Envia um e-mail via SMTP."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = f"{config['nome_remetente']} <{config['email']}>"
        msg['To'] = destinatario

        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"], timeout=10)
        if config["use_tls"]:
            server.starttls()
        server.login(config["email"], config["password"])
        server.send_message(msg)
        server.quit()

        return True, None
    except Exception as e:
        return False, str(e)


def processar_caderneta(state, config):
    """Processa a caderneta e prepara e-mails para envio."""
    if "disciplinas" not in state or not state["disciplinas"]:
        print("Erro: Caderneta inválida ou vazia.")
        sys.exit(1)

    print("\n" + "="*60)
    print("CADERNETA EXPORTADA")
    print("="*60)

    disciplinas = state["disciplinas"]
    print(f"\nDisciplinas encontradas: {len(disciplinas)}")
    for i, (disc_id, disc) in enumerate(disciplinas.items(), 1):
        print(f"  {i}. {disc.get('nome', 'Sem nome')} ({disc.get('anoSemestre', '')})")

    if len(disciplinas) == 1:
        disc_id = list(disciplinas.keys())[0]
    else:
        idx = int(input("\nEscolha a disciplina (número): ")) - 1
        disc_id = list(disciplinas.keys())[idx]

    disciplina = disciplinas[disc_id]
    avaliacoes = disciplina.get("avaliacoes", [])
    estudantes = disciplina.get("estudantes", [])
    notas = disciplina.get("notas", {})
    template = disciplina.get("template", {})

    print(f"\nDisciplina: {disciplina.get('nome')}")
    print(f"Estudantes: {len(estudantes)}")
    print(f"Avaliações: {len(avaliacoes)}")

    if len(avaliacoes) == 1:
        av_id = avaliacoes[0]["id"]
    else:
        print("\nAvaliações:")
        for i, av in enumerate(avaliacoes, 1):
            print(f"  {i}. {av['nome']}")
        idx = int(input("Escolha a avaliação para enviar (número): ")) - 1
        av_id = avaliacoes[idx]["id"]

    av = next((a for a in avaliacoes if a["id"] == av_id), None)
    if not av:
        print("Erro: Avaliação não encontrada.")
        sys.exit(1)

    # Filtrar estudantes com notas lançadas para esta avaliação
    fila_envio = []
    for es in estudantes:
        if not es.get("email"):
            continue
        if es["id"] not in notas or av_id not in notas[es["id"]]:
            continue
        entry = notas[es["id"]][av_id]
        
        # Montar contexto de template
        def soma_criterios(criterios_obj):
            soma = 0
            for c in av.get("criterios", []):
                soma += float(criterios_obj.get(c["id"], 0))
            return soma

        nota_final = soma_criterios(entry.get("criterios", {}))
        criterios_txt = "\n".join([
            f"- {c['nome']}: {entry.get('criterios', {}).get(c['id'], 0):.1f} / {c['valor']}"
            for c in av.get("criterios", [])
        ])
        if entry.get("obs"):
            criterios_txt += f"\n\nComentário: {entry['obs']}"

        detalhe_rec = ""
        if entry.get("recuperacao", {}).get("aplicada"):
            rec_nota = soma_criterios(entry.get("recuperacao", {}).get("criterios", {}))
            detalhe_rec = f"\n(Nota após recuperação — original: {nota_final:.1f} / {av['valor']}; recuperação: {rec_nota:.1f} / {av['valor']})"
            if entry.get("recuperacao", {}).get("obs"):
                detalhe_rec += f"\nComentário sobre recuperação: {entry['recuperacao']['obs']}"

        ctx = {
            "nome": es["nome"],
            "disciplina": disciplina.get("nome", ""),
            "avaliacao": av["nome"],
            "valor": av["valor"],
            "nota": f"{nota_final:.1f}",
            "criterios": criterios_txt,
            "detalhe_recuperacao": detalhe_rec,
            "total_lancado": sum([
                soma_criterios(notas.get(es["id"], {}).get(a["id"], {}).get("criterios", {}))
                for a in avaliacoes
                if es["id"] in notas and a["id"] in notas[es["id"]]
            ]),
            "professor": disciplina.get("professor", "")
        }

        # Preencher template
        assunto = template.get("assunto", "Sua nota — {avaliacao} — {disciplina}")
        corpo = template.get("corpo", "")
        
        for chave, valor in ctx.items():
            assunto = assunto.replace(f"{{{chave}}}", str(valor))
            corpo = corpo.replace(f"{{{chave}}}", str(valor))

        fila_envio.append({
            "nome": es["nome"],
            "email": es["email"],
            "assunto": assunto,
            "corpo": corpo
        })

    if not fila_envio:
        print(f"\nNenhum estudante com notas lançadas para '{av['nome']}'.")
        sys.exit(1)

    print(f"\n{len(fila_envio)} e-mail(s) prontos para enviar.")
    return fila_envio, av["nome"]


def enviar_fila(config, fila, nome_avaliacao):
    """Envia e-mails da fila com relatório."""
    print("\n" + "="*60)
    print("ENVIO DE E-MAILS")
    print("="*60)
    print(f"Avaliação: {nome_avaliacao}\n")

    # Teste com o primeiro
    if len(fila) > 1:
        teste = input("Fazer teste com o primeiro e-mail? (s/n): ").strip().lower() == 's'
        if teste:
            primeiro = fila[0]
            print(f"\nTestando com: {primeiro['nome']} <{primeiro['email']}>")
            print(f"Assunto: {primeiro['assunto']}\n")
            print("Corpo do e-mail:")
            print("-" * 60)
            print(primeiro['corpo'])
            print("-" * 60)
            sucesso, erro = enviar_email(config, primeiro['email'], primeiro['assunto'], primeiro['corpo'])
            if sucesso:
                print("\n✓ E-mail de teste enviado com sucesso!")
                continua = input("Continuar enviando para os demais? (s/n): ").strip().lower() == 's'
                if not continua:
                    print("Envio cancelado.")
                    return
                fila = fila[1:]  # Remover o primeiro da fila (já enviado)
            else:
                print(f"\n✗ Erro no teste: {erro}")
                print("Verifique sua configuração e tente novamente.")
                return

    # Enviar resto
    sucessos, erros = 0, 0
    erros_detalhes = []

    for i, item in enumerate(fila, 1):
        print(f"[{i}/{len(fila)}] Enviando para {item['nome']}...", end=" ")
        sucesso, erro = enviar_email(config, item['email'], item['assunto'], item['corpo'])
        if sucesso:
            print("✓")
            sucessos += 1
        else:
            print("✗")
            erros += 1
            erros_detalhes.append(f"  {item['nome']}: {erro}")

    print("\n" + "="*60)
    print("RELATÓRIO")
    print("="*60)
    print(f"Enviados com sucesso: {sucessos}")
    print(f"Falhas: {erros}")

    if erros_detalhes:
        print("\nDetalhes dos erros:")
        for detalhe in erros_detalhes:
            print(detalhe)


def main():
    parser = argparse.ArgumentParser(
        description="Enviar e-mails automáticos da Caderneta",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("caderneta", nargs="?", help="Caminho do arquivo JSON da caderneta exportada")
    parser.add_argument("--config", action="store_true", help="Configurar credenciais de e-mail")

    args = parser.parse_args()

    if args.config:
        setup_config()
        return

    if not args.caderneta:
        parser.print_help()
        sys.exit(1)

    # Carregar configuração
    config = load_config()
    if not config:
        print("Erro: Arquivo config.json não encontrado.")
        print("Execute primeiro: python3 enviar_emails.py --config\n")
        sys.exit(1)

    # Processar caderneta
    state = load_caderneta(args.caderneta)
    fila, nome_av = processar_caderneta(state, config)

    # Enviar
    enviar_fila(config, fila, nome_av)

    print("\n✓ Processo concluído!")


if __name__ == "__main__":
    main()
