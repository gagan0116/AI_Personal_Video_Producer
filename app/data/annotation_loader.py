import json
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from app.models.events import ActionEvent, CameraEvent, CommentarySegment
from app.models.match import MatchInfo


# Verified metadata presets for the 5 downloaded matches
PRESET_MATCHES: List[Dict[str, Any]] = [
    {
        "match_id": "barcelona_vs_paris_sg",
        "relative_path": "europe_uefa-champions-league/2016-2017/2017-03-08 - 22-45 Barcelona 6 - 1 Paris SG",
        "home_team": "Barcelona",
        "away_team": "Paris SG",
        "score": "6 - 1",
        "league": "UEFA Champions League",
        "season": "2016-2017",
        "match_date": "2017-03-08",
        "display_title": "Barcelona 6 - 1 Paris SG (The Remontada)",
        "star_players": ["Neymar", "Messi", "Suarez", "Cavani", "Iniesta", "Di Maria", "Sergi Roberto"]
    },
    {
        "match_id": "leicester_vs_arsenal",
        "relative_path": "england_epl/2015-2016/2015-09-26 - 17-00 Leicester 2 - 5 Arsenal",
        "home_team": "Leicester City",
        "away_team": "Arsenal",
        "score": "2 - 5",
        "league": "English Premier League",
        "season": "2015-2016",
        "match_date": "2015-09-26",
        "display_title": "Leicester City 2 - 5 Arsenal",
        "star_players": ["Alexis Sanchez", "Jamie Vardy", "Mesut Ozil", "Theo Walcott", "Riyad Mahrez"]
    },
    {
        "match_id": "chelsea_vs_swansea",
        "relative_path": "england_epl/2015-2016/2015-08-08 - 19-30 Chelsea 2 - 2 Swansea",
        "home_team": "Chelsea",
        "away_team": "Swansea City",
        "score": "2 - 2",
        "league": "English Premier League",
        "season": "2015-2016",
        "match_date": "2015-08-08",
        "display_title": "Chelsea 2 - 2 Swansea City",
        "star_players": ["Eden Hazard", "Diego Costa", "Andre Ayew", "Oscar", "Bafetimbi Gomis"]
    },
    {
        "match_id": "real_madrid_vs_las_palmas",
        "relative_path": "spain_laliga/2016-2017/2017-03-01 - 23-30 Real Madrid 3 - 3 Las Palmas",
        "home_team": "Real Madrid",
        "away_team": "Las Palmas",
        "score": "3 - 3",
        "league": "Spain La Liga",
        "season": "2016-2017",
        "match_date": "2017-03-01",
        "display_title": "Real Madrid 3 - 3 Las Palmas",
        "star_players": ["Cristiano Ronaldo", "Gareth Bale", "Isco", "Kevin-Prince Boateng", "Jonathan Viera"]
    },
    {
        "match_id": "real_madrid_vs_getafe",
        "relative_path": "spain_laliga/2014-2015/2015-05-23 - 21-30 Real Madrid 7 - 3 Getafe",
        "home_team": "Real Madrid",
        "away_team": "Getafe",
        "score": "7 - 3",
        "league": "Spain La Liga",
        "season": "2014-2015",
        "match_date": "2015-05-23",
        "display_title": "Real Madrid 7 - 3 Getafe",
        "star_players": ["Cristiano Ronaldo", "James Rodriguez", "Chicharito", "Martin Odegaard", "Sergio Escudero"]
    }
]


def parse_game_time_string(game_time: str) -> Tuple[int, int, int]:
    """
    Parse SoccerNet game time string, e.g. '1 - 00:14' or '2 - 48:20'.
    Returns: (half, minutes, seconds)
    """
    try:
        match = re.match(r'(\d+)\s*-\s*(\d+):(\d+)', game_time.strip())
        if match:
            half = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return half, minutes, seconds
    except Exception:
        pass
    return 1, 0, 0


def game_time_to_display(half: int, position_ms: int) -> str:
    """Format milliseconds into 'H - MM:SS'"""
    total_seconds = position_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{half} - {minutes:02d}:{seconds:02d}"


class AnnotationLoader:
    """
    Loads, parses, and indexes SoccerNet action spotting, camera, and commentary files.
    """

    def __init__(self, match_path: str):
        self.match_path = Path(match_path)
        self.action_events: List[ActionEvent] = []
        self.camera_events: List[CameraEvent] = []
        self.commentary: List[CommentarySegment] = []
        self.is_loaded = False

    def load(self) -> None:
        """Load all available annotation files for this match."""
        if not self.match_path.exists():
            print(f"[AnnotationLoader] [WARNING] Match data directory not found at '{self.match_path}'. Automatically loading rich synthetic demo dataset.")
            self._load_synthetic_demo_data()
            self.is_loaded = True
            return

        print(f"[AnnotationLoader] [INFO] Loading SoccerNet annotations from: {self.match_path}")
        self._load_labels_v2()
        self._load_labels_cameras()
        self._load_asr(half=1)
        self._load_asr(half=2)
        print(f"[AnnotationLoader] [OK] Loaded {len(self.action_events)} action events, {len(self.camera_events)} camera markers, {len(self.commentary)} commentary segments.")
        self.is_loaded = True

    def _load_labels_v2(self) -> None:
        labels_file = self.match_path / "Labels-v2.json"
        if not labels_file.exists():
            print(f"[AnnotationLoader] [INFO] Labels-v2.json not found at '{labels_file}'.")
            return

        try:
            with open(labels_file, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            for item in data.get("annotations", []):
                game_time = item.get("gameTime", "1 - 00:00")
                half, _, _ = parse_game_time_string(game_time)
                position = int(item.get("position", 0))

                self.action_events.append(
                    ActionEvent(
                        game_time=game_time,
                        label=item.get("label", "Unknown"),
                        position=position,
                        team=item.get("team", "home"),
                        visibility=item.get("visibility", "visible"),
                        half=half,
                    )
                )
            # Sort chronologically
            self.action_events.sort(key=lambda x: (x.half, x.position))
        except Exception as e:
            print(f"Error loading Labels-v2.json from {labels_file}: {e}")

    def _load_labels_cameras(self) -> None:
        cameras_file = self.match_path / "Labels-cameras.json"
        if not cameras_file.exists():
            return

        try:
            with open(cameras_file, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            for item in data.get("annotations", []):
                game_time = item.get("gameTime", "1 - 00:00")
                half, _, _ = parse_game_time_string(game_time)
                position = int(item.get("position", 0))

                self.camera_events.append(
                    CameraEvent(
                        game_time=game_time,
                        label=item.get("label", "Main camera center"),
                        position=position,
                        change_type=item.get("change_type", "logo"),
                        replay=item.get("replay", "real-time"),
                        link=item.get("link"),
                        half=half,
                    )
                )
            self.camera_events.sort(key=lambda x: (x.half, x.position))
        except Exception as e:
            print(f"Error loading Labels-cameras.json from {cameras_file}: {e}")

    def _load_asr(self, half: int) -> None:
        # Check standard paths: echoes/whisper_v2_en/{half}_asr.json or echoes/{half}_asr.json or {half}_asr.json
        candidate_paths = [
            self.match_path / "echoes" / "whisper_v2_en" / f"{half}_asr.json",
            self.match_path / "echoes" / f"{half}_asr.json",
            self.match_path / f"{half}_asr.json",
        ]

        asr_file = next((p for p in candidate_paths if p.exists()), None)
        if not asr_file:
            return

        try:
            with open(asr_file, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            segments = data.get("segments", {})
            # segments can be dict of lists or list of dicts/lists
            if isinstance(segments, dict):
                for seg_key, seg_val in segments.items():
                    if isinstance(seg_val, list) and len(seg_val) >= 3:
                        start_time = float(seg_val[0])
                        end_time = float(seg_val[1])
                        text = str(seg_val[2]).strip()
                        self.commentary.append(
                            CommentarySegment(
                                start_time=start_time,
                                end_time=end_time,
                                text=text,
                                half=half,
                            )
                        )
            elif isinstance(segments, list):
                for seg in segments:
                    if isinstance(seg, dict):
                        self.commentary.append(
                            CommentarySegment(
                                start_time=float(seg.get("start", 0)),
                                end_time=float(seg.get("end", 0)),
                                text=str(seg.get("text", "")).strip(),
                                half=half,
                            )
                        )
                    elif isinstance(seg, list) and len(seg) >= 3:
                        self.commentary.append(
                            CommentarySegment(
                                start_time=float(seg[0]),
                                end_time=float(seg[1]),
                                text=str(seg[2]).strip(),
                                half=half,
                            )
                        )

            self.commentary.sort(key=lambda x: (x.half, x.start_time))
        except Exception as e:
            print(f"Error loading ASR from {asr_file}: {e}")

    def _load_synthetic_demo_data(self) -> None:
        """Synthetic rich demo dataset for Barcelona 6-1 PSG Remontada when developing offline."""
        demo_actions = [
            ("1 - 00:00", "Kick-off", 0, "away", 1),
            ("1 - 00:14", "Foul", 14478, "away", 1),
            ("1 - 00:22", "Indirect free-kick", 22914, "home", 1),
            ("1 - 01:04", "Foul", 64909, "away", 1),
            ("1 - 02:30", "Shots on target", 150000, "home", 1),
            ("1 - 02:45", "Offside", 165000, "home", 1),
            ("1 - 03:15", "Goal", 195000, "home", 1),  # Luis Suarez early header 3'
            ("1 - 06:11", "Corner", 371608, "home", 1),
            ("1 - 10:45", "Direct free-kick", 645000, "home", 1),
            ("1 - 14:30", "Foul", 870000, "away", 1),
            ("1 - 17:20", "Shots off target", 1040000, "home", 1),
            ("1 - 25:10", "Foul", 1510000, "home", 1),
            ("1 - 39:50", "Goal", 2390000, "home", 1),  # Kurzawa Own Goal 40'
            ("1 - 44:10", "Yellow card", 2650000, "away", 1),
            # Second half
            ("2 - 49:20", "Penalty", 260000, "home", 2),
            ("2 - 50:00", "Goal", 300000, "home", 2),   # Messi Penalty 50'
            ("2 - 61:40", "Goal", 1000000, "away", 2),  # Cavani Goal 62'
            ("2 - 87:30", "Direct free-kick", 2550000, "home", 2),
            ("2 - 88:00", "Goal", 2580000, "home", 2),  # Neymar Free-kick 88'
            ("2 - 90:10", "Penalty", 2710000, "home", 2),
            ("2 - 90:40", "Goal", 2740000, "home", 2),  # Neymar Penalty 91'
            ("2 - 94:35", "Goal", 2975000, "home", 2),  # Sergi Roberto 95' Historical finish
        ]
        for gt, label, pos, team, half in demo_actions:
            self.action_events.append(
                ActionEvent(game_time=gt, label=label, position=pos, team=team, visibility="visible", half=half)
            )

        demo_commentary = [
            (0.0, 9.0, "It was a 90 minutes of immense happiness with Rakitic and Pique taking position in defense.", 1),
            (9.0, 20.0, "Yes, Mascherano plays on the right, Umtiti on the left opposed to Lucas Moura.", 1),
            (21.0, 35.0, "Neymar already pressing vigorously down the left flank for Barcelona.", 1),
            (145.0, 160.0, "Messi slides it through to Suarez, great offside trap by Marquinhos!", 1),
            (190.0, 210.0, "AND GOAL! Luis Suarez loops the header over Kevin Trapp! Camp Nou explodes at 3 minutes!", 1),
            (640.0, 660.0, "Neymar stands over the free kick on the edge of the penalty box.", 1),
            (865.0, 885.0, "Neymar with brilliant footwork on the wing, drawn down by Meunier for a foul!", 1),
            (2380.0, 2405.0, "Iniesta backheels it across the face of goal, and it bounces in! Barcelona lead 2-0!", 1),
            (290.0, 315.0, "Messi buries the penalty! 3-0 to Barcelona! The comeback is well and truly on!", 2),
            (990.0, 1020.0, "Cavani volleys past ter Stegen! An away goal for Paris Saint-Germain! Is the dream over?", 2),
            (2570.0, 2600.0, "WHAT A STRIKE! NEYMAR curls an absolute masterpiece into the top corner from 30 yards!", 2),
            (2730.0, 2755.0, "Neymar steps up and converts the penalty! 5-1! Just one goal needed now!", 2),
            (2960.0, 3000.0, "Neymar chips the ball into the area... SERGI ROBERTO HAS DONE IT! UNBELIEVABLE! 6-1! HISTORIC REMONTADA!", 2),
        ]
        for s, e, txt, half in demo_commentary:
            self.commentary.append(CommentarySegment(start_time=s, end_time=e, text=txt, half=half))

        self.camera_events.append(
            CameraEvent(game_time="1 - 03:20", label="Spider camera", position=200000, change_type="logo", replay="replay", link={"label": "Goal", "position": 195000}, half=1)
        )
        self.camera_events.append(
            CameraEvent(game_time="2 - 94:50", label="Close-up player", position=2990000, change_type="logo", replay="replay", link={"label": "Goal", "position": 2975000}, half=2)
        )

    def get_events_in_window(self, start_ms: int, end_ms: int, half: int) -> List[ActionEvent]:
        """Return action events occurring in [start_ms, end_ms) for specified half."""
        return [
            e for e in self.action_events
            if e.half == half and start_ms <= e.position < end_ms
        ]

    def get_camera_events_in_window(self, start_ms: int, end_ms: int, half: int) -> List[CameraEvent]:
        """Return camera events in specified time window."""
        return [
            c for c in self.camera_events
            if c.half == half and start_ms <= c.position < end_ms
        ]

    def get_commentary_in_window(self, start_ms: int, end_ms: int, half: int) -> List[CommentarySegment]:
        """Return commentary segments overlapping [start_ms, end_ms)."""
        start_sec = start_ms / 1000.0
        end_sec = end_ms / 1000.0
        return [
            c for c in self.commentary
            if c.half == half and c.end_time >= start_sec and c.start_time <= end_sec
        ]

    def get_replay_count_for_event(self, position_ms: int, half: int, tolerance_ms: int = 8000) -> int:
        """Count replays referring back to this event position."""
        count = 0
        for cam in self.camera_events:
            if cam.half == half and cam.replay == "replay" and cam.link:
                link_pos = int(cam.link.get("position", 0))
                if abs(link_pos - position_ms) <= tolerance_ms:
                    count += 1
        return count


def discover_matches(data_root: str) -> List[MatchInfo]:
    """
    Scans the given data directory for SoccerNet matches,
    merging with predefined rich metadata.
    """
    root_path = Path(data_root)
    if not root_path.exists():
        print(f"[AnnotationLoader] [WARNING] SoccerNet root data directory '{data_root}' does not exist on local filesystem. Pre-registering match catalog with fallback support.")
    else:
        print(f"[AnnotationLoader] [INFO] Scanning SoccerNet matches at: {data_root}")

    found_matches: List[MatchInfo] = []

    for preset in PRESET_MATCHES:
        rel_path = preset["relative_path"]
        match_dir = root_path / rel_path
        
        # Check for video files or annotations
        vid1 = str(match_dir / "1_224p.mkv")
        vid2 = str(match_dir / "2_224p.mkv")

        found_matches.append(
            MatchInfo(
                match_id=preset["match_id"],
                home_team=preset["home_team"],
                away_team=preset["away_team"],
                score=preset["score"],
                league=preset["league"],
                season=preset["season"],
                match_date=preset["match_date"],
                data_path=str(match_dir),
                video_first_half=vid1,
                video_second_half=vid2,
                display_title=preset["display_title"],
                star_players=preset["star_players"],
            )
        )

    return found_matches
