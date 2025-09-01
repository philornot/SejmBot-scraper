# !/usr/bin/env python3
# main.py
"""
SejmBotScraper - Narzędzie do pobierania stenogramów z Sejmu RP

Główny plik uruchamiający program do pobierania stenogramów
z API Sejmu Rzeczypospolitej Polskiej.
"""

import argparse
import logging
import sys
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR, DEFAULT_TERM
from scraper import SejmScraper


def setup_logging(verbose: bool = False, log_file: str = None):
    """
    Konfiguruje system logowania

    Args:
        verbose: czy wyświetlać szczegółowe logi
        log_file: ścieżka do pliku z logami (opcjonalne)
    """
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL.upper())

    # Konfiguracja podstawowa
    handlers = [logging.StreamHandler(sys.stdout)]

    # Dodaj handler pliku jeśli podano
    if log_file:
        log_path = Path(LOGS_DIR) / log_file
        handlers.append(logging.FileHandler(log_path, encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=handlers
    )


def print_banner():
    """Wyświetla banner aplikacji"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                        SejmBotScraper                        ║
║                                                              ║
║          Narzędzie do pobierania stenogramów Sejmu RP        ║
║                     Wersja 1.0                               ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Główna funkcja programu"""
    parser = argparse.ArgumentParser(
        description="SejmBotScraper - pobiera stenogramy z API Sejmu RP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s                              # pobierz całą 10. kadencję (tylko PDF)
  %(prog)s -t 9                         # pobierz 9. kadencję
  %(prog)s -t 10 -p 15                  # pobierz posiedzenie 15 z 10. kadencji
  %(prog)s -t 10 --statements           # pobierz także wypowiedzi HTML
  %(prog)s --list-terms                 # wyświetl dostępne kadencje
  %(prog)s -t 10 --summary              # wyświetl podsumowanie posiedzeń
  %(prog)s -v --log-file scraper.log    # verbose z zapisem do pliku
        """
    )

    # Główne opcje
    parser.add_argument(
        '-t', '--term',
        type=int,
        default=DEFAULT_TERM,
        help=f'Numer kadencji do pobrania (domyślnie: {DEFAULT_TERM})'
    )

    parser.add_argument(
        '-p', '--proceeding',
        type=int,
        help='Numer konkretnego posiedzenia do pobrania (opcjonalne)'
    )

    # Opcje pobierania
    parser.add_argument(
        '--no-pdfs',
        action='store_true',
        help='Nie pobieraj plików PDF (domyślnie pobierane)'
    )

    parser.add_argument(
        '--statements',
        action='store_true',
        help='Pobierz także poszczególne wypowiedzi w HTML (domyślnie nie)'
    )

    # Opcje informacyjne
    parser.add_argument(
        '--list-terms',
        action='store_true',
        help='Wyświetl listę dostępnych kadencji i zakończ'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Wyświetl podsumowanie posiedzeń dla danej kadencji'
    )

    # Opcje logowania
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Szczegółowe logi (DEBUG level)'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Zapisuj logi do pliku (w katalogu logs/)'
    )

    args = parser.parse_args()

    # Konfiguruj logowanie
    setup_logging(args.verbose, args.log_file)

    # Wyświetl banner
    if not args.list_terms and not args.summary:
        print_banner()

    # Utwórz scraper
    scraper = SejmScraper()

    try:
        # Lista kadencji
        if args.list_terms:
            terms = scraper.get_available_terms()
            if terms:
                print("Dostępne kadencje Sejmu RP:")
                print("-" * 50)
                for term in terms:
                    current = " (OBECNA)" if term.get('current') else ""
                    print(f"Kadencja {term['num']:2d}: {term.get('from', '?')} - {term.get('to', 'trwa')}{current}")
            else:
                print("Nie można pobrać listy kadencji.")
            return

        # Podsumowanie posiedzeń
        if args.summary:
            summary = scraper.get_term_proceedings_summary(args.term)
            if summary:
                print(f"Posiedzenia kadencji {args.term}:")
                print("-" * 60)
                for proc in summary:
                    current = " [TRWA]" if proc.get('current') else ""
                    dates_str = ", ".join(proc['dates']) if proc['dates'] else "brak dat"
                    print(f"Posiedzenie {proc['number']:3d}: {dates_str}{current}")
                    if proc.get('title'):
                        print(f"    Tytuł: {proc['title'][:80]}{'...' if len(proc['title']) > 80 else ''}")
                    print()
            else:
                print(f"Nie można pobrać informacji o posiedzeniach kadencji {args.term}.")
            return

        # Główny proces scrapowania
        logging.info("Rozpoczynanie procesu pobierania stenogramów...")

        download_pdfs = not args.no_pdfs
        download_statements = args.statements

        if args.proceeding:
            # Pobierz konkretne posiedzenie
            success = scraper.scrape_specific_proceeding(
                args.term,
                args.proceeding,
                download_pdfs,
                download_statements
            )

            if success:
                print(f"\n✅ Pomyślnie pobrano posiedzenie {args.proceeding} z kadencji {args.term}")
            else:
                print(f"\n❌ Błąd podczas pobierania posiedzenia {args.proceeding}")
                sys.exit(1)
        else:
            # Pobierz całą kadencję
            stats = scraper.scrape_term(args.term, download_pdfs, download_statements)

            print(f"\n📊 PODSUMOWANIE POBIERANIA KADENCJI {args.term}")
            print("=" * 50)
            print(f"Przetworzone posiedzenia: {stats['proceedings_processed']}")
            print(f"Pobrane PDF-y:           {stats['pdfs_downloaded']}")
            print(f"Zapisane wypowiedzi:     {stats['statements_saved']}")
            print(f"Błędy:                   {stats['errors']}")
            print("=" * 50)

            if stats['errors'] > 0:
                print(f"⚠️  Proces zakończony z {stats['errors']} błędami. Sprawdź logi.")
            else:
                print("✅ Proces zakończony pomyślnie!")

    except KeyboardInterrupt:
        logging.info("Proces przerwany przez użytkownika (Ctrl+C)")
        print("\n\n⏹️  Proces przerwany przez użytkownika.")
        sys.exit(1)

    except Exception as e:
        logging.exception("Nieoczekiwany błąd programu")
        print(f"\n❌ Nieoczekiwany błąd: {e}")
        print("Sprawdź logi dla szczegółów.")
        sys.exit(1)


if __name__ == "__main__":
    main()
