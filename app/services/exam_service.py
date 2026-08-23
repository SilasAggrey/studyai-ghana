"""Exam scoring (Phase 2 foundation). Pure functions, easily unit-tested."""


def grade_for(percentage: float) -> str:
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B+"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C+"
    if percentage >= 40:
        return "C"
    return "F"


def compute_exam_result(score: int, total: int, time_used_minutes: int) -> dict:
    percentage = round(score / total * 100, 1) if total else 0.0
    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "grade": grade_for(percentage),
        "correct": score,
        "wrong": total - score,
        "time_used_minutes": time_used_minutes,
    }
