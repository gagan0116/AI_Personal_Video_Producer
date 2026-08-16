import re
from typing import List, Set, Dict, Optional


# Pre-populated verified rosters for the 5 SoccerNet matches in the dataset
ROSTERS: Dict[str, Dict[str, List[str]]] = {
    # Match: Barcelona 6 - 1 Paris SG (2017-03-08)
    "barcelona_vs_paris_sg": {
        "home": [
            "Neymar", "Messi", "Lionel Messi", "Suarez", "Luis Suarez", "Luis Suárez",
            "Iniesta", "Andres Iniesta", "Rakitic", "Ivan Rakitic", "Busquets", "Sergio Busquets",
            "Pique", "Gerard Pique", "Piqué", "Mascherano", "Javier Mascherano",
            "Umtiti", "Samuel Umtiti", "Rafinha", "ter Stegen", "Marc-Andre ter Stegen",
            "Sergi Roberto", "Roberto", "Arda Turan", "Andre Gomes"
        ],
        "away": [
            "Cavani", "Edinson Cavani", "Di Maria", "Angel Di Maria", "Ángel Di María",
            "Draxler", "Julian Draxler", "Verratti", "Marco Verratti", "Rabiot", "Adrien Rabiot",
            "Matuidi", "Blaise Matuidi", "Lucas", "Lucas Moura", "Marquinhos",
            "Thiago Silva", "Meunier", "Thomas Meunier", "Kurzawa", "Layvin Kurzawa",
            "Trapp", "Kevin Trapp", "Aurier", "Krychowiak"
        ]
    },
    # Match: Leicester 2 - 5 Arsenal (2015-09-26)
    "leicester_vs_arsenal": {
        "home": [
            "Vardy", "Jamie Vardy", "Mahrez", "Riyad Mahrez", "Okazaki", "Shinji Okazaki",
            "Drinkwater", "Danny Drinkwater", "Kante", "N'Golo Kante", "Kanté",
            "Albrighton", "Marc Albrighton", "Schmeichel", "Kasper Schmeichel",
            "Morgan", "Wes Morgan", "Huth", "Robert Huth", "Fuchs", "Christian Fuchs",
            "De Laet", "King", "Ulloa", "Kramaric"
        ],
        "away": [
            "Sanchez", "Alexis Sanchez", "Alexis Sánchez", "Walcott", "Theo Walcott",
            "Ozil", "Mesut Ozil", "Mesut Özil", "Giroud", "Olivier Giroud",
            "Cazorla", "Santi Cazorla", "Ramsey", "Aaron Ramsey", "Flamini", "Mathieu Flamini",
            "Coquelin", "Francis Coquelin", "Bellerin", "Hector Bellerin",
            "Monreal", "Nacho Monreal", "Koscielny", "Laurent Koscielny",
            "Mertesacker", "Per Mertesacker", "Cech", "Petr Cech", "Oxlade-Chamberlain"
        ]
    },
    # Match: Chelsea 2 - 2 Swansea (2015-08-08)
    "chelsea_vs_swansea": {
        "home": [
            "Hazard", "Eden Hazard", "Diego Costa", "Costa", "Oscar", "Willian",
            "Fabregas", "Cesc Fabregas", "Cesc Fàbregas", "Matic", "Nemanja Matic",
            "Courtois", "Thibaut Courtois", "Begovic", "Asmir Begovic", "Terry", "John Terry",
            "Cahill", "Gary Cahill", "Ivanovic", "Branislav Ivanovic", "Azpilicueta", "Cesar Azpilicueta",
            "Falcao", "Radamel Falcao", "Ramires", "Zouma"
        ],
        "away": [
            "Ayew", "Andre Ayew", "Gomis", "Bafetimbi Gomis", "Montero", "Jefferson Montero",
            "Sigurdsson", "Gylfi Sigurdsson", "Shelvey", "Jonjo Shelvey", "Ki", "Ki Sung-yueng",
            "Cork", "Jack Cork", "Fabianski", "Lukasz Fabianski", "Williams", "Ashley Williams",
            "Fernandez", "Federico Fernandez", "Naughton", "Kyle Naughton", "Taylor", "Neil Taylor",
            "Routledge", "Eder"
        ]
    },
    # Match: Real Madrid 3 - 3 Las Palmas (2017-03-01)
    "real_madrid_vs_las_palmas": {
        "home": [
            "Cristiano", "Ronaldo", "Cristiano Ronaldo", "Bale", "Gareth Bale",
            "Morata", "Alvaro Morata", "Isco", "Kroos", "Toni Kroos", "Kovacic", "Mateo Kovacic",
            "Modric", "Luka Modric", "Marcelo", "Ramos", "Sergio Ramos",
            "Nacho", "Carvajal", "Dani Carvajal", "Navas", "Keylor Navas",
            "Benzema", "Karim Benzema", "James", "James Rodriguez", "Lucas Vazquez"
        ],
        "away": [
            "Boateng", "Kevin-Prince Boateng", "Jese", "Jesé", "Viera", "Jonathan Viera",
            "Tana", "Roque Mesa", "Vicente Gomez", "David Simon", "Lemos", "Mauricio Lemos",
            "Bigas", "Pedro Bigas", "Dani Castellano", "Varas", "Javi Varas", "Halilovic"
        ]
    },
    # Match: Real Madrid 7 - 3 Getafe (2015-05-23)
    "real_madrid_vs_getafe": {
        "home": [
            "Ronaldo", "Cristiano Ronaldo", "Cristiano", "Chicharito", "Javier Hernandez",
            "James", "James Rodriguez", "Jese", "Jesé", "Kroos", "Toni Kroos", "Illarramendi",
            "Marcelo", "Pepe", "Nacho", "Arbeloa", "Casillas", "Iker Casillas",
            "Odegaard", "Martin Odegaard", "Martin Ødegaard", "Silva", "Lucas Silva"
        ],
        "away": [
            "Escudero", "Sergio Escudero", "Castro", "Diego Castro", "Lacen", "Mehdi Lacen",
            "Pedro Leon", "Pedro León", "Sarabi", "Pablo Sarabia", "Hinestroza",
            "Codina", "Jordi Codina", "Alexis", "Vigaray", "Naldo", "Alex Felip"
        ]
    }
}


class PlayerExtractor:
    """
    Extracts, normalizes, and matches player mentions across ASR transcripts
    and user queries.
    """

    def __init__(self, match_slug: Optional[str] = None):
        self.match_slug = match_slug or ""
        self.known_players: Set[str] = set()
        self._populate_roster()

    def _populate_roster(self):
        # Match slug normalization
        clean_slug = self.match_slug.lower().replace("-", "_").replace(" ", "_")
        matched_key = None
        for key in ROSTERS:
            if key in clean_slug or any(part in clean_slug for part in key.split("_vs_")):
                matched_key = key
                break

        if matched_key and matched_key in ROSTERS:
            for team_role in ("home", "away"):
                for p in ROSTERS[matched_key][team_role]:
                    self.known_players.add(p)
        else:
            # Add all known players from all rosters as fallback
            for match_roster in ROSTERS.values():
                for team_role in ("home", "away"):
                    for p in match_roster[team_role]:
                        self.known_players.add(p)

    def extract_players(self, text: str) -> List[str]:
        """Extract matched player names from text."""
        if not text:
            return []

        found: List[str] = []
        text_lower = f" {text.lower()} "

        # Check against known players
        for player in sorted(self.known_players, key=len, reverse=True):
            # Match whole word
            pattern = r'\b' + re.escape(player.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found.append(player)

        # Deduplicate while preserving specificity (prefer longer names, e.g. "Cristiano Ronaldo" over "Ronaldo")
        unique_results: List[str] = []
        for p in sorted(found, key=len, reverse=True):
            if not any(p.lower() in existing.lower() for existing in unique_results):
                unique_results.append(p)

        return unique_results

    def is_player_mentioned(self, text: str, target_player: str) -> bool:
        """Check if target player (or any alias/part) is in text."""
        if not text or not target_player:
            return False
        
        target_clean = target_player.strip().lower()
        parts = [p for p in re.split(r'\s+', target_clean) if len(p) > 2]
        
        text_lower = text.lower()
        if target_clean in text_lower:
            return True
        
        # Check individual meaningful parts (e.g. "Neymar" in "Neymar Jr")
        return any(part in text_lower for part in parts)
