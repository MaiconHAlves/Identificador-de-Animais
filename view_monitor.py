"""
Dashboard ao vivo do monitor de treino.
Atualiza a cada 30s exibindo training_monitor_report.md no terminal.

Uso: py -3.12 view_monitor.py
"""
import os, re, time, sys

REPORT      = r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\training_monitor_report.md"
SUCCESS     = r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\SUCCESS.md"
ESCALATE    = r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\ESCALATE.md"
LOG         = r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\training_full.log"
QWEN_LOG    = r"c:\Users\alves\Desktop\Projetos\Identificador de Animais\qwen_monitor.log"
REFRESH     = 30  # segundos

sys.stdout.reconfigure(encoding='utf-8')


def cls():
    os.system('cls')


def read_file(path, tail_lines=None):
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        if tail_lines:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - tail_lines * 120))
        content = f.read().decode('utf-8', errors='replace')
    if tail_lines:
        return '\n'.join(content.split('\n')[-tail_lines:])
    return content


def last_epoch_from_log():
    content = read_file(LOG, tail_lines=80)
    if not content:
        return "log nao encontrado"
    import re
    lines = content.split('\n')
    epoch_lines = [l.strip() for l in lines if re.search(r'\s+\d+/50\s', l)]
    return epoch_lines[-1] if epoch_lines else "aguardando primeiro epoch..."


def header(ts, cycle):
    w = 64
    print("=" * w)
    print(f"  MONITOR DE TREINO YOLOv8 — v2 (95 classes)")
    print(f"  Atualizado: {ts}  |  Ciclo #{cycle}  |  Refresh: {REFRESH}s")
    print("=" * w)


def main():
    cycle = 0
    print("Dashboard iniciado. Aguardando primeiro relatorio da Qwen...")
    print(f"Ctrl+C para sair.\n")

    while True:
        try:
            cycle += 1
            ts = time.strftime('%H:%M:%S')
            cls()
            header(ts, cycle)

            # Verificar SUCCESS/ESCALATE primeiro
            if os.path.exists(SUCCESS):
                print("\n[SUCESSO] Treino concluido!\n")
                print(read_file(SUCCESS))
                print("\nPressione Ctrl+C para sair.")
                time.sleep(REFRESH)
                continue

            if os.path.exists(ESCALATE):
                print("\n[!] ESCALATE detectado!\n")
                print(read_file(ESCALATE))
                print("\nAguardando Qwen resolver ou intervencao manual...")
                time.sleep(REFRESH)
                continue

            # Relatório da Qwen
            report = read_file(REPORT)
            if report:
                print(report)
            else:
                # Qwen ainda não gerou relatório — mostrar log diretamente
                print("\n[Aguardando primeiro relatorio da Qwen...]\n")
                print("Ultima linha do log de treino:")
                print(f"  {last_epoch_from_log()}")
                print(f"\nInicie a Qwen com:")
                print(f"  py -3.12 qwen.py --light --task QWEN_MONITOR_TASK.md")

            print(f"\n{'─' * 64}")
            print(f"  Proximo refresh em {REFRESH}s  |  Ctrl+C para sair")

                # Últimas ações da Qwen
            qwen = read_file(QWEN_LOG, tail_lines=12)
            if qwen:
                print(f"\n{'─' * 64}")
                print("  QWEN MONITOR (últimas ações):")
                for line in qwen.strip().split('\n')[-10:]:
                    clean = re.sub(r'\x1b\[[0-9;]*[mKABCDHJfsu]', '', line).strip()
                    if clean:
                        print(f"  {clean[:80]}")

        except KeyboardInterrupt:
            print("\nDashboard encerrado.")
            sys.exit(0)
        except Exception as e:
            print(f"\nErro: {e}")

        time.sleep(REFRESH)


if __name__ == "__main__":
    main()
