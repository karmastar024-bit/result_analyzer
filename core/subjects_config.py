"""User-specified curriculum and analytical settings; not official policy advice."""

PASS_PERCENT = 40
IDENTITY = ["Student ID", "Student Name", "Gender", "Residence", "Section"]
STAGES = {
    "Key Stage 1": {
        "classes": ["PP", "I", "II", "III"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science & Technology",
            "Health & Physical Education",
            "Arts Education",
        ],
    },
    "Key Stage 2": {
        "classes": ["IV", "V", "VI"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science",
            "Social Studies (History & Geography)",
            "Health & Physical Education",
            "Arts Education & ICT",
        ],
    },
    "Key Stage 3": {
        "classes": ["VII", "VIII"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science",
            "History",
            "Geography",
            "Health & Physical Education",
            "Digital Technology / ICT",
        ],
    },
    "Key Stage 4": {
        "classes": ["IX", "X"],
        "core": [
            "Dzongkha",
            "English",
            "Mathematics",
            "Science (Physics, Chemistry, Biology)",
            "History & Geography",
        ],
        "pathways": {
            "General School Pathway": {
                "core": ["Economics", "Digital Technology & Innovation"]
            },
            "TVET School Pathway": {
                "core": ["TVET"],
                "options": ["Economics"],
                "min": 0,
                "max": 1,
            },
        },
    },
    "Key Stage 5": {
        "classes": ["XI", "XII"],
        "core": ["Dzongkha", "English"],
        "pathways": {
            "Science": {
                "core": ["Physics", "Chemistry"],
                "options": ["Biology", "Mathematics", "DTI", "Rigzhung", "TVET"],
                "min": 1,
                "max": 2,
            },
            "Commerce": {
                "core": ["Commerce", "Accountancy"],
                "options": [
                    "Economics",
                    "Business Mathematics / Math",
                    "DTI",
                    "Rigzhung",
                    "TVET",
                ],
                "min": 1,
                "max": 2,
            },
            "Arts/Humanities": {
                "core": [],
                "options": [
                    "Geography",
                    "History",
                    "Economics",
                    "Business Mathematics / Math",
                    "English Literature",
                    "Rigzhung",
                    "DTI",
                    "TVET",
                ],
                "min": 3,
                "max": 4,
            },
        },
    },
}
DIAGNOSIS = {
    "urgent_pass": 60,
    "urgent_mean": 45,
    "improve_pass": 75,
    "improve_mean": 55,
    "well_pass": 90,
    "well_mean": 65,
    "high_std": 20,
    "group_gap": 10,
    "pass_benchmark": 75,
}
COLORS = {
    "Male": "#3288D1",
    "Female": "#D84B9B",
    "Boarder": "#2C9B73",
    "Day Scholar": "#E88A32",
}
METHODS = (
    "Pass threshold: 40% (inclusive). All subject statistics use percentage marks. "
    "Blank/AB marks are excluded independently per subject, never converted to zero. "
    "Standard deviation uses ddof=1 and is unavailable for n<2. "
    "Student averages equally weight available subject percentages; total marks and "
    "rankings require complete records. Passed all subjects uses complete students; "
    "passed at least one uses students with at least one valid mark. "
    "Overall mean/median/std use available student averages. "
    "IQR outliers lie below Q1-1.5×IQR or above Q3+1.5×IQR. "
    "Subject strength = 0.5×mean + 0.5×pass%. "
    "Section composite = 0.4×all-subject pass% + 0.3×mean + 0.2×median "
    "+ 0.1×max(0,100-std). A section needs at least two assessed students and "
    "one complete student to receive a composite. Ties share competition rank. "
    "Diagnosis applies urgent and improvement rules first, then Doing Well; "
    "all remaining combinations are Satisfactory. Comparisons are descriptive, not causal."
)


def resolve_subjects(
    stage: str, pathway: str = "", choices: list[str] | None = None, tvet: str = ""
) -> list[str]:
    """Validate elective counts and resolve the school-specific TVET column."""
    config = STAGES[stage]
    result = list(config["core"])
    if "pathways" in config:
        path = config["pathways"][pathway]
        choices = choices or []
        if not path.get("min", 0) <= len(choices) <= path.get("max", 0):
            raise ValueError(
                f"Choose {path.get('min', 0)}–{path.get('max', 0)} optional subjects."
            )
        if any(c not in path.get("options", []) for c in choices):
            raise ValueError("An optional subject is not valid for this pathway.")
        result += path["core"] + choices
    if "TVET" in result:
        if not tvet.strip():
            raise ValueError("Enter the school-specific TVET subject name.")
        result = [tvet.strip() if s == "TVET" else s for s in result]
    keys = [s.strip().casefold() for s in result]
    if len(keys) != len(set(keys)) or set(keys) & {
        s.casefold() for s in IDENTITY + ["Overall", "Overall average"]
    }:
        raise ValueError(
            "Subject names must be unique and distinct from identity columns."
        )
    return result
