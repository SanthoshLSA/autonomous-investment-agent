"""
Report Generator Orchestrator.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.logger import get_logger
from src.reports.html_report import generate_html_report

logger = get_logger(__name__)


def generate_daily_report(state_data: dict[str, Any]) -> dict[str, Any]:
    """Orchestrates report file creation (HTML).

    Args:
        state_data: Analysis output dictionary.

    Returns:
        Dictionary mapping formats ('html') to their output file paths.
    """
    logger.info("Starting daily report generation...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Establish output directory structure
    out_dir = Path("reports/output") / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    
    html_path = out_dir / "report.html"
    
    # Render HTML file
    generate_html_report(state_data, html_path)
    
    logger.info("Daily report generation complete", html_path=str(html_path))
    return {
        "html": str(html_path.resolve()),
    }
