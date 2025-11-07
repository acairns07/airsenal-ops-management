"""Output parser for AIrsenal CLI commands."""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from utils.logging import get_logger

logger = get_logger(__name__)


class OutputParser:
    """Parse AIrsenal CLI output into structured data."""

    def __init__(self):
        self.ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

    def clean_line(self, line: str) -> str:
        """
        Remove ANSI escape codes and clean a line.

        Args:
            line: Raw line from CLI output

        Returns:
            Cleaned line
        """
        cleaned = self.ansi_escape.sub('', line.replace('\r', ''))
        return cleaned.strip()

    def parse(self, command: str, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parse command output.

        Args:
            command: Command type (predict, optimize, etc.)
            parameters: Command parameters
            logs: Command output logs

        Returns:
            Parsed output dictionary or None
        """
        try:
            if command == "predict":
                return self._parse_prediction(parameters, logs)
            elif command == "optimize":
                return self._parse_optimization(parameters, logs)
            return None
        except Exception as e:
            logger.error(f"Failed to parse {command} output: {e}", exc_info=True)
            return None

    def _parse_prediction(self, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        """Parse prediction output."""
        cleaned_lines: List[str] = []
        for raw_line in logs:
            cleaned = self.clean_line(raw_line)
            if cleaned:
                cleaned_lines.append(cleaned)

        start_idx = next((idx for idx, value in enumerate(cleaned_lines)
                          if value.upper().startswith("PREDICTED TOP")), None)
        if start_idx is None:
            logger.warning("No prediction output found in logs")
            return None

        summary_lines: List[str] = []
        for line in cleaned_lines[start_idx:]:
            summary_lines.append(line)
            if line.lower().startswith("persisted db"):
                break

        headline = summary_lines[0] if summary_lines else ""
        player_pattern = re.compile(r"^\s*(\d+)\.\s*(?P<player>[^,]+),\s*(?P<points>[-+]?\d+(?:\.\d+)?)pts", re.IGNORECASE)
        players: List[Dict[str, Any]] = []
        current_position: Optional[str] = None
        rank_counter = 1

        for line in summary_lines[1:]:
            if not line or set(line) == {'-'}:
                continue
            if line.endswith(':') and line[:-1].isupper():
                current_position = line[:-1]
                continue
            match = player_pattern.match(line)
            if not match:
                continue
            try:
                points_value = float(match.group('points'))
            except ValueError:
                points_value = None
            player_entry: Dict[str, Any] = {
                "rank": rank_counter,
                "player": match.group('player').strip(),
                "expected_points": points_value,
            }
            if current_position:
                player_entry["position"] = current_position
            players.append(player_entry)
            rank_counter += 1

        summary_text = "\n".join(summary_lines).strip()
        logger.info(f"Parsed prediction with {len(players)} players")
        return {
            "type": "prediction",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "parameters": parameters,
            "headline": headline,
            "players": players,
            "summary_text": summary_text,
        }

    def _parse_optimization(self, parameters: Dict[str, Any], logs: List[str]) -> Optional[Dict[str, Any]]:
        """Parse optimization output."""
        cleaned_lines: List[str] = []
        for raw_line in logs:
            cleaned = self.clean_line(raw_line)
            if cleaned:
                cleaned_lines.append(cleaned)

        summary_lines: List[str] = []
        capture = False
        for line in cleaned_lines:
            if not capture and line.startswith("Strategy for Team ID"):
                capture = True
            if capture:
                summary_lines.append(line)
                if line.lower().startswith("persisted db"):
                    break

        if not summary_lines:
            logger.warning("No optimization output found in logs")
            return None

        summary_text = "\n".join(summary_lines).strip()
        baseline_match = re.search(r"Baseline score:\s*([-+]?\d+(?:\.\d+)?)", summary_text)
        best_match = re.search(r"Best score:\s*([-+]?\d+(?:\.\d+)?)", summary_text)
        total_match = re.search(r"Total score:\s*([-+]?\d+(?:\.\d+)?)", summary_text)
        baseline_points = float(baseline_match.group(1)) if baseline_match else None
        best_points = float(best_match.group(1)) if best_match else None
        expected_points = float(total_match.group(1)) if total_match else best_points

        transfers: List[Dict[str, str]] = []
        try:
            transfer_idx = next(idx for idx, value in enumerate(summary_lines)
                                 if value.lower().startswith("players in"))
        except StopIteration:
            transfer_idx = None

        if transfer_idx is not None:
            for line in summary_lines[transfer_idx + 2:]:
                if not line or line.startswith("=") or line.startswith("Total score") or line.startswith("Getting starting squad") or line.lower().startswith("total progress"):
                    break
                if set(line.replace('\t', '').strip()) == {'-'}:
                    continue
                parts = [part.strip() for part in re.split(r"\s{2,}|\t+", line) if part.strip()]
                if not parts:
                    continue
                in_player = parts[0]
                out_player = parts[1] if len(parts) > 1 else ""
                transfers.append({
                    "in": in_player,
                    "out": out_player,
                })

        captain = None
        vice_captain = None
        starting_lineup: List[Dict[str, str]] = []
        bench: List[Dict[str, str]] = []
        current_group: Optional[str] = None
        in_starting_section = False

        for line in summary_lines:
            if line.startswith("=== starting 11"):
                in_starting_section = True
                current_group = None
                continue
            if not in_starting_section:
                continue
            if line.startswith("=== subs"):
                current_group = "Subs"
                continue
            if line.startswith("=="):
                current_group = line.strip('=').strip()
                continue
            if not line or line.startswith("Persisted DB"):
                continue
            if line.lower().startswith("total progress"):
                break
            if set(line.replace('\t', '').strip()) == {'-'}:
                continue
            name = re.sub(r"\s*\(VC\)|\s*\(C\)", "", line).strip()
            if not name:
                continue
            entry = {"name": name, "position_group": current_group or ""}
            if current_group == "Subs":
                bench.append(entry)
            else:
                starting_lineup.append(entry)
            if "(C)" in line and not captain:
                captain = name
            if "(VC)" in line and not vice_captain:
                vice_captain = name

        result: Dict[str, Any] = {
            "type": "optimisation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "parameters": parameters,
            "transfers": transfers,
            "captain": captain,
            "vice_captain": vice_captain,
            "expected_points": expected_points,
            "summary_text": summary_text,
        }
        if baseline_points is not None:
            result["baseline_points"] = baseline_points
        if best_points is not None:
            result["best_points"] = best_points
        if starting_lineup:
            result["starting_lineup"] = starting_lineup
        if bench:
            result["bench"] = bench

        logger.info(f"Parsed optimization with {len(transfers)} transfers")
        return result


# Global parser instance
output_parser = OutputParser()
