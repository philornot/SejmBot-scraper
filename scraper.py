# scraper.py
"""
Główna logika scrapowania stenogramów Sejmu RP
"""

import logging
from typing import List, Dict, Optional

from config import DEFAULT_TERM
from file_manager import FileManager
from sejm_api import SejmAPI

logger = logging.getLogger(__name__)


class SejmScraper:
    """Główna klasa do scrapowania stenogramów Sejmu"""

    def __init__(self):
        self.api = SejmAPI()
        self.file_manager = FileManager()
        self.stats = {
            'proceedings_processed': 0,
            'pdfs_downloaded': 0,
            'statements_saved': 0,
            'errors': 0
        }

    def scrape_term(self, term: int = DEFAULT_TERM, download_pdfs: bool = True,
                    download_statements: bool = False) -> Dict:
        """
        Scrapuje wszystkie stenogramy z danej kadencji

        Args:
            term: numer kadencji
            download_pdfs: czy pobierać pliki PDF
            download_statements: czy pobierać poszczególne wypowiedzi HTML

        Returns:
            Statystyki procesu
        """
        logger.info(f"Rozpoczynanie scrapowania kadencji {term}")

        # Pobierz informacje o kadencji
        term_info = self.api.get_term_info(term)
        if not term_info:
            logger.error(f"Nie można pobrać informacji o kadencji {term}")
            return self.stats

        logger.info(f"Kadencja {term}: {term_info.get('from', '')} - {term_info.get('to', 'obecna')}")

        # Pobierz listę posiedzeń
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            logger.error(f"Nie można pobrać listy posiedzeń dla kadencji {term}")
            return self.stats

        logger.info(f"Znaleziono {len(proceedings)} posiedzeń")

        # Przetwarzaj każde posiedzenie
        for proceeding in proceedings:
            try:
                self._process_proceeding(term, proceeding, download_pdfs, download_statements)
                self.stats['proceedings_processed'] += 1
            except Exception as e:
                logger.error(f"Błąd przetwarzania posiedzenia {proceeding.get('number', '?')}: {e}")
                self.stats['errors'] += 1

        self._log_final_stats()
        return self.stats

    def scrape_specific_proceeding(self, term: int, proceeding_number: int,
                                   download_pdfs: bool = True, download_statements: bool = False) -> bool:
        """
        Scrapuje konkretne posiedzenie

        Args:
            term: numer kadencji
            proceeding_number: numer posiedzenia
            download_pdfs: czy pobierać pliki PDF
            download_statements: czy pobierać poszczególne wypowiedzi HTML

        Returns:
            True jeśli sukces, False w przeciwnym przypadku
        """
        logger.info(f"Scrapowanie posiedzenia {proceeding_number} z kadencji {term}")

        # Znajdź posiedzenie o danym numerze
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            logger.error(f"Nie można pobrać listy posiedzeń dla kadencji {term}")
            return False

        target_proceeding = None
        for proceeding in proceedings:
            if proceeding.get('number') == proceeding_number:
                target_proceeding = proceeding
                break

        if not target_proceeding:
            logger.error(f"Nie znaleziono posiedzenia {proceeding_number} w kadencji {term}")
            return False

        try:
            self._process_proceeding(term, target_proceeding, download_pdfs, download_statements)
            self.stats['proceedings_processed'] += 1
            logger.info(f"Zakończono przetwarzanie posiedzenia {proceeding_number}")
            return True
        except Exception as e:
            logger.error(f"Błąd przetwarzania posiedzenia {proceeding_number}: {e}")
            self.stats['errors'] += 1
            return False

    def _process_proceeding(self, term: int, proceeding: Dict,
                            download_pdfs: bool, download_statements: bool):
        """
        Przetwarza jedno posiedzenie

        Args:
            term: numer kadencji
            proceeding: informacje o posiedzeniu
            download_pdfs: czy pobierać PDF-y
            download_statements: czy pobierać wypowiedzi HTML
        """
        proceeding_number = proceeding.get('number')
        logger.info(f"Przetwarzanie posiedzenia {proceeding_number}")

        # Pobierz szczegółowe informacje o posiedzeniu
        detailed_info = self.api.get_proceeding_info(term, proceeding_number)
        if not detailed_info:
            logger.warning(f"Nie można pobrać szczegółów posiedzenia {proceeding_number}")
            detailed_info = proceeding  # użyj podstawowych informacji

        # Zapisz informacje o posiedzeniu
        self.file_manager.save_proceeding_info(term, proceeding_number, detailed_info)

        # Pobierz daty posiedzenia
        dates = detailed_info.get('dates', [])
        if not dates:
            logger.warning(f"Brak dat dla posiedzenia {proceeding_number}")
            return

        logger.info(f"Posiedzenie {proceeding_number} trwało {len(dates)} dni: {dates}")

        # Przetwarzaj każdy dzień posiedzenia
        for date in dates:
            self._process_proceeding_day(term, proceeding_number, date,
                                         detailed_info, download_pdfs, download_statements)

    def _process_proceeding_day(self, term: int, proceeding_id: int, date: str,
                                proceeding_info: Dict, download_pdfs: bool, download_statements: bool):
        """
        Przetwarza jeden dzień posiedzenia

        Args:
            term: numer kadencji
            proceeding_id: ID posiedzenia
            date: data w formacie YYYY-MM-DD
            proceeding_info: informacje o posiedzeniu
            download_pdfs: czy pobierać PDF
            download_statements: czy pobierać wypowiedzi HTML
        """
        logger.info(f"Przetwarzanie dnia {date} posiedzenia {proceeding_id}")

        # Pobierz transkrypt PDF jeśli wymagany
        if download_pdfs:
            self._download_pdf_transcript(term, proceeding_id, date, proceeding_info)

        # Pobierz wypowiedzi HTML jeśli wymagane
        if download_statements:
            self._download_html_statements(term, proceeding_id, date, proceeding_info)

    def _download_pdf_transcript(self, term: int, proceeding_id: int, date: str, proceeding_info: Dict):
        """Pobiera transkrypt PDF dla danego dnia"""
        try:
            logger.debug(f"Pobieranie PDF dla {date}")
            pdf_content = self.api.get_transcript_pdf(term, proceeding_id, date)

            if pdf_content:
                saved_path = self.file_manager.save_pdf_transcript(
                    term, proceeding_id, date, pdf_content, proceeding_info
                )
                if saved_path:
                    self.stats['pdfs_downloaded'] += 1
                    logger.info(f"Pobrano PDF: {saved_path}")
                else:
                    logger.warning(f"Nie udało się zapisać PDF dla {date}")
            else:
                logger.warning(f"Brak treści PDF dla {date}")

        except Exception as e:
            logger.error(f"Błąd pobierania PDF dla {date}: {e}")
            self.stats['errors'] += 1

    def _download_html_statements(self, term: int, proceeding_id: int, date: str, proceeding_info: Dict):
        """Pobiera wypowiedzi HTML dla danego dnia"""
        try:
            logger.debug(f"Pobieranie wypowiedzi HTML dla {date}")
            statements = self.api.get_transcripts_list(term, proceeding_id, date)

            if statements:
                saved_path = self.file_manager.save_html_statements(
                    term, proceeding_id, date, statements, proceeding_info
                )
                if saved_path:
                    statement_count = len(statements.get('statements', []))
                    self.stats['statements_saved'] += statement_count
                    logger.info(f"Zapisano {statement_count} wypowiedzi do: {saved_path}")
                else:
                    logger.warning(f"Nie udało się zapisać wypowiedzi dla {date}")
            else:
                logger.warning(f"Brak wypowiedzi dla {date}")

        except Exception as e:
            logger.error(f"Błąd pobierania wypowiedzi HTML dla {date}: {e}")
            self.stats['errors'] += 1

    def _log_final_stats(self):
        """Loguje końcowe statystyki"""
        logger.info("=== STATYSTYKI KOŃCOWE ===")
        logger.info(f"Przetworzone posiedzenia: {self.stats['proceedings_processed']}")
        logger.info(f"Pobrane PDF-y: {self.stats['pdfs_downloaded']}")
        logger.info(f"Zapisane wypowiedzi: {self.stats['statements_saved']}")
        logger.info(f"Błędy: {self.stats['errors']}")
        logger.info("=========================")

    def get_available_terms(self) -> Optional[List[Dict]]:
        """
        Pobiera listę dostępnych kadencji

        Returns:
            Lista kadencji lub None w przypadku błędu
        """
        return self.api.get_terms()

    def get_term_proceedings_summary(self, term: int) -> Optional[List[Dict]]:
        """
        Pobiera podsumowanie posiedzeń dla kadencji

        Args:
            term: numer kadencji

        Returns:
            Lista z podstawowymi informacjami o posiedzeniach
        """
        proceedings = self.api.get_proceedings(term)
        if not proceedings:
            return None

        summary = []
        for proc in proceedings:
            summary.append({
                'number': proc.get('number'),
                'title': proc.get('title', ''),
                'dates': proc.get('dates', []),
                'current': proc.get('current', False)
            })

        return summary
