import json
import re
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
REF_DIR = BASE_DIR / "data" / "reference"

REF_DIR.mkdir(parents=True, exist_ok=True)


def remove_comments(text):
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def strip_strings(value):
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return [strip_strings(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key).strip(): strip_strings(val)
            for key, val in value.items()
        }

    return value


def clean_pairs(pairs):
    cleaned = {}

    for key, value in pairs:
        cleaned_key = str(key).strip()
        cleaned_value = strip_strings(value)
        cleaned[cleaned_key] = cleaned_value

    return cleaned


def load_raw_json(path):
    text = path.read_text(encoding="utf-8-sig")
    text = remove_comments(text)

    try:
        return json.loads(text, object_pairs_hook=clean_pairs)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON decoding error in {path.name}: {exc}")


def normalize_curriculum(data):
    levels = data.get("didactic_programs_by_level", {})

    for level_code, level_data in levels.items():
        units = level_data.get("units", [])

        for unit in units:
            sub_modules = unit.get("sub_modules", [])

            for sub_module in sub_modules:
                competency_value = sub_module.get("competency", "")

                if competency_value:
                    codes = [
                        code.strip().upper()
                        for code in str(competency_value).split(",")
                        if code.strip()
                    ]
                    sub_module["competency_codes"] = codes

                elif "competency_codes" in sub_module:
                    sub_module["competency_codes"] = [
                        str(code).strip().upper()
                        for code in sub_module["competency_codes"]
                    ]

    return data


def validate_curriculum(data):
    report = {"errors": [], "warnings": []}

    framework_codes = set()
    for domain in data.get("competency_framework", {}).get("domains_of_action", []):
        for competency in domain.get("competencies", []):
            code = str(competency.get("code", "")).strip().upper()
            if code:
                framework_codes.add(code)
                competency["code"] = code

    all_topic_ids = set()
    levels = data.get("didactic_programs_by_level", {})
    for level_data in levels.values():
        for unit in level_data.get("units", []):
            for sm in unit.get("sub_modules", []):
                if sm.get("topic_id"):
                    all_topic_ids.add(sm["topic_id"])

    VALID_MILESTONES = {"diagnostic", "S1_CC", "S2_CC"}

    for level_code, level_data in levels.items():
        semester_hours = {1: 0, 2: 0}
        calculated = 0

        for unit in level_data.get("units", []):
            for sm in unit.get("sub_modules", []):
                tid = sm.get("topic_id", "unknown")

                try:
                    hours = int(sm.get("allocated_hours", 0))
                    calculated += hours
                except Exception:
                    hours = 0
                    report["errors"].append(f"{level_code} {tid}: invalid allocated_hours")

                sem = sm.get("semester")
                if sem not in (1, 2):
                    report["errors"].append(f"{level_code} {tid}: missing/invalid semester")
                else:
                    semester_hours[sem] += hours

                if sm.get("period") not in ("P1", "P2"):
                    report["warnings"].append(f"{level_code} {tid}: missing/invalid period")

                milestone = sm.get("eval_milestone")
                if milestone not in VALID_MILESTONES:
                    report["errors"].append(f"{level_code} {tid}: invalid eval_milestone")
                elif sem == 1 and milestone == "S2_CC":
                    report["warnings"].append(f"{level_code} {tid}: semester-1 module tagged S2_CC")
                elif sem == 2 and milestone == "S1_CC":
                    report["warnings"].append(f"{level_code} {tid}: semester-2 module tagged S1_CC")

                for code in sm.get("competency_codes", []):
                    if code not in framework_codes:
                        report["warnings"].append(f"{level_code} {tid}: unknown competency {code}")

                for pre in sm.get("prerequisites", []):
                    if pre not in all_topic_ids:
                        report["errors"].append(f"{level_code} {tid}: unknown prerequisite {pre}")

        if calculated != int(level_data.get("total_hours", 30)):
            report["errors"].append(
                f"{level_code}: calculated {calculated}h != total_hours {level_data.get('total_hours')}"
            )

        report["warnings"].append(
            f"{level_code}: semester split S1={semester_hours[1]}h / S2={semester_hours[2]}h"
        )

    return report


def validate_calendar(data, curriculum_data=None):
    report = {"errors": [], "warnings": []}

    # 1. Holidays (existing logic)
    holidays = data.get("official_holidays", [])
    for holiday in holidays:
        holiday_id = holiday.get("id", "unknown")
        holiday_name = holiday.get("name", "unknown holiday")
        try:
            start_date = date.fromisoformat(str(holiday.get("start_date")))
        except Exception:
            report["errors"].append(f"Holiday {holiday_id} ({holiday_name}): invalid start_date")
            continue
        try:
            end_date = date.fromisoformat(str(holiday.get("end_date")))
        except Exception:
            report["errors"].append(f"Holiday {holiday_id} ({holiday_name}): invalid end_date")
            continue
        if end_date < start_date:
            report["errors"].append(f"Holiday {holiday_id} ({holiday_name}): end_date is before start_date")
        if holiday.get("is_estimated"):
            report["warnings"].append(f"Holiday {holiday_id} ({holiday_name}): date is estimated")

    # 2. Assessment windows
    for w_id, w in data.get("assessment_windows", {}).items():
        try:
            s = date.fromisoformat(str(w.get("start")))
            e = date.fromisoformat(str(w.get("end")))
            if e < s:
                report["errors"].append(f"Assessment window {w_id}: end before start")
        except Exception:
            report["errors"].append(f"Assessment window {w_id}: invalid date format")

    # 3. Extracurricular & competitions
    framework_codes = set()
    if curriculum_data:
        for domain in curriculum_data.get("competency_framework", {}).get("domains_of_action", []):
            for comp in domain.get("competencies", []):
                framework_codes.add(str(comp.get("code", "")).strip().upper())

    for event in data.get("extracurricular_and_competitions", []):
        e_id = event.get("id", "unknown")
        w = event.get("window", {})
        try:
            s = date.fromisoformat(str(w.get("start")))
            e = date.fromisoformat(str(w.get("end")))
            if e < s:
                report["errors"].append(f"Extracurricular {e_id}: end before start")
        except Exception:
            report["errors"].append(f"Extracurricular {e_id}: invalid date format")

        for lvl in event.get("levels", []):
            if lvl not in ("1AC", "2AC", "3AC"):
                report["errors"].append(f"Extracurricular {e_id}: invalid level {lvl}")

        for comp in event.get("related_competencies", []):
            if framework_codes and comp.upper() not in framework_codes:
                report["warnings"].append(f"Extracurricular {e_id}: unknown competency {comp}")

        if event.get("is_estimated"):
            report["warnings"].append(f"Extracurricular {e_id}: date is estimated")

    return report

    holidays = data.get("official_holidays", [])

    for holiday in holidays:
        holiday_id = holiday.get("id", "unknown")
        holiday_name = holiday.get("name", "unknown holiday")

        start_date_text = holiday.get("start_date")
        end_date_text = holiday.get("end_date")

        try:
            start_date = date.fromisoformat(str(start_date_text))
        except Exception:
            report["errors"].append(
                f"Holiday {holiday_id} ({holiday_name}): invalid start_date"
            )
            continue

        try:
            end_date = date.fromisoformat(str(end_date_text))
        except Exception:
            report["errors"].append(
                f"Holiday {holiday_id} ({holiday_name}): invalid end_date"
            )
            continue

        if end_date < start_date:
            report["errors"].append(
                f"Holiday {holiday_id} ({holiday_name}): end_date is before start_date"
            )

        if holiday.get("is_estimated"):
            report["warnings"].append(
                f"Holiday {holiday_id} ({holiday_name}): date is estimated"
            )

    return report


def validate_pedagogy(data):
    report = {
        "errors": [],
        "warnings": []
    }

    schema_version = data.get("schema_version", 1)

    # Core framework validation (both v1 and v2)
    framework = data.get("pedagogical_planning_framework", {})

    moments = framework.get("three_moments_of_learning", [])
    if len(moments) != 3:
        report["warnings"].append(
            "three_moments_of_learning should contain exactly 3 moments"
        )

    files = framework.get("three_mandatory_preparation_files", {})
    if len(files) != 3:
        report["warnings"].append(
            "three_mandatory_preparation_files should contain exactly 3 files"
        )

    expected_files = [
        "fiche_ressources",
        "fiche_integration",
        "fiche_evaluation"
    ]

    for expected in expected_files:
        if expected not in files:
            report["errors"].append(
                f"Missing mandatory preparation file: {expected}"
            )

    # v2-specific validations (optional blocks)
    if schema_version >= 2:
        v2_blocks = [
            "institutional_context",
            "competencies_taxonomy",
            "curricular_matrix_by_level",
            "didactic_methodologies",
            "competency_specific_didactic_orientations",
            "laboratory_management_guidelines"
        ]

        present_blocks = [block for block in v2_blocks if block in data]
        
        if present_blocks:
            report["warnings"].append(
                f"Schema v2 detected with blocks: {', '.join(present_blocks)}"
            )

        # Validate competencies_taxonomy if present
        if "competencies_taxonomy" in data:
            taxonomy = data["competencies_taxonomy"]
            competencies_list = taxonomy.get("competencies_list", {})
            
            expected_codes = ["C0", "C11", "C12", "C13", "C21", "C22", "C23", "C31", "C32", "C33"]
            missing_codes = [code for code in expected_codes if code not in competencies_list]
            
            if missing_codes:
                report["warnings"].append(
                    f"competencies_taxonomy missing codes: {', '.join(missing_codes)}"
                )

        # Validate curricular_matrix_by_level if present
        if "curricular_matrix_by_level" in data:
            matrix = data["curricular_matrix_by_level"]
            expected_levels = ["1AC", "2AC", "3AC"]
            missing_levels = [lvl for lvl in expected_levels if lvl not in matrix]
            
            if missing_levels:
                report["warnings"].append(
                    f"curricular_matrix_by_level missing levels: {', '.join(missing_levels)}"
                )
            
            # Check 30-hour totals
            for level_code in expected_levels:
                if level_code in matrix:
                    total = matrix[level_code].get("volume_horaire_total", 0)
                    if total != 30:
                        report["warnings"].append(
                            f"{level_code}: volume_horaire_total is {total}, expected 30"
                        )

    return report


def main():



    files_to_process = {
        "curriculum_pilot.json": {
            "output": "curriculum_clean.json",
            "normalizer": normalize_curriculum,
            "validator": validate_curriculum
        },
        "academic_calendar.json": {
            "output": "calendar_clean.json",
            "normalizer": None,
            "validator": validate_calendar
        },
        "institutional_memory.json": {
            "output": "pedagogy_clean.json",
            "normalizer": None,
            "validator": validate_pedagogy
        }
    }

    validation_reports = {}

    for raw_file_name, config in files_to_process.items():
        raw_path = RAW_DIR / raw_file_name

        if not raw_path.exists():
            print(f"MISSING FILE: {raw_path}")
            validation_reports[config["output"]] = {
                "errors": [
                    f"Raw file not found: {raw_file_name}"
                ],
                "warnings": []
            }
            continue

        data = load_raw_json(raw_path)

        if config["normalizer"]:
            data = config["normalizer"](data)

        output_path = REF_DIR / config["output"]

        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"CLEANED: {output_path}")

        if config["validator"]:
            if config["output"] == "calendar_clean.json":
                curriculum_data = None
                try:
                    curriculum_data = load_raw_json(RAW_DIR / "curriculum_pilot.json")
                except Exception:
                    curriculum_data = None
                report = config["validator"](data, curriculum_data)
            else:
                report = config["validator"](data)
        else:
            report = {
                "errors": [],
                "warnings": []
            }

        validation_reports[config["output"]] = report

        for error in report["errors"]:
            print(f"ERROR [{config['output']}] {error}")

        for warning in report["warnings"]:
            print(f"WARNING [{config['output']}] {warning}")

    report_path = REF_DIR / "validation_report.json"

    report_path.write_text(
        json.dumps(validation_reports, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"VALIDATION REPORT: {report_path}")
    print("DONE")


if __name__ == "__main__":
    main()
