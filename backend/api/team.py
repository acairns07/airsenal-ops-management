"""Team API routes."""
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
import httpx

from auth import get_current_user
from utils.logging import get_logger
from utils.encryption import decrypt_secret

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database instance."""
    from database import db
    return db


@router.get("/current")
async def get_current_team(
    current_user: str = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get current FPL team from Fantasy Premier League API.

    Args:
        current_user: Current authenticated user
        db: Database instance

    Returns:
        Current team data

    Raises:
        HTTPException: If team ID not configured or API fetch fails
    """
    team_id_doc = await db.secrets.find_one({"key": "FPL_TEAM_ID"})
    if not team_id_doc or not team_id_doc.get("value"):
        raise HTTPException(status_code=404, detail="FPL team ID not configured")

    # Try to decrypt team ID
    try:
        team_id = decrypt_secret(team_id_doc.get("value")).strip()
    except Exception:
        # Fall back to unencrypted (for backwards compatibility)
        team_id = str(team_id_doc.get("value")).strip()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get bootstrap data (players, teams, events)
            bootstrap_resp = await client.get('https://fantasy.premierleague.com/api/bootstrap-static/')
            bootstrap_resp.raise_for_status()
            bootstrap_data = bootstrap_resp.json()

            # Determine current gameweek
            current_event = next((event for event in bootstrap_data.get('events', []) if event.get('is_current')), None)
            if not current_event:
                current_event = next((event for event in bootstrap_data.get('events', []) if event.get('is_next')), None)
            if not current_event and bootstrap_data.get('events'):
                current_event = bootstrap_data['events'][-1]

            if not current_event:
                raise HTTPException(status_code=502, detail="Unable to determine current gameweek")

            event_id = current_event['id']

            # Get team picks for current gameweek
            picks_resp = await client.get(f'https://fantasy.premierleague.com/api/entry/{team_id}/event/{event_id}/picks/')
            picks_resp.raise_for_status()
            picks_data = picks_resp.json()

    except httpx.HTTPError as exc:
        logger.error(
            f"Failed to fetch FPL data: {exc}",
            extra={'user_email': current_user, 'team_id': team_id},
            exc_info=True
        )
        raise HTTPException(status_code=502, detail=f'Failed to fetch FPL data: {exc}') from exc

    # Build lookup tables
    elements = {element['id']: element for element in bootstrap_data.get('elements', [])}
    teams = {team['id']: team for team in bootstrap_data.get('teams', [])}
    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

    # Process picks
    picks = sorted(picks_data.get('picks', []), key=lambda item: item.get('position', 0))
    players = []
    for pick in picks:
        element = elements.get(pick.get('element'))
        if not element:
            continue
        team_info = teams.get(element.get('team'), {})
        try:
            points_per_game = float(element.get('points_per_game', '0') or 0)
        except ValueError:
            points_per_game = 0.0
        player_entry = {
            'position_slot': pick.get('position'),
            'player_id': pick.get('element'),
            'name': element.get('web_name'),
            'team': team_info.get('short_name'),
            'position': position_map.get(element.get('element_type'), str(element.get('element_type'))),
            'multiplier': pick.get('multiplier', 0),
            'is_captain': pick.get('is_captain', False),
            'is_vice_captain': pick.get('is_vice_captain', False),
            'now_cost': element.get('now_cost', 0) / 10 if element.get('now_cost') is not None else None,
            'points_per_game': points_per_game,
            'event_points': element.get('event_points'),
        }
        players.append(player_entry)

    # Extract entry history/summary
    history = picks_data.get('entry_history', {})

    def _to_value(raw):
        return raw / 10 if isinstance(raw, (int, float)) else None

    entry_summary = {
        'bank': _to_value(history.get('bank')),
        'team_value': _to_value(history.get('value')),
        'total_points': history.get('total_points'),
        'event_points': history.get('points'),
        'event_transfers': history.get('event_transfers'),
        'event_transfers_cost': history.get('event_transfers_cost'),
        'points_on_bench': history.get('points_on_bench'),
    }

    logger.info(f"Retrieved team data", extra={'user_email': current_user, 'team_id': team_id})

    return {
        'team_id': team_id,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'gameweek': {
            'id': current_event.get('id'),
            'name': current_event.get('name'),
            'deadline': current_event.get('deadline_time'),
            'is_current': current_event.get('is_current'),
        },
        'players': players,
        'entry_summary': entry_summary,
    }
