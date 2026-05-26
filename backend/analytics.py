"""
Analytics tracker — persists finding counts via raw SQL (bypasses ORM issues).
"""
import os
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/primoauditai.db")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def track_audit_findings(findings: list, claim_number: str = "", file_type: str = ""):
    """Record findings via raw SQL insert."""
    db = Session()
    try:
        for f in findings:
            db.execute(text(
                "INSERT INTO analytics_logs (rule_id, severity, category, claim_number, file_type, timestamp) "
                "VALUES (:rid, :sev, :cat, :cn, :ft, NOW())"
            ), {
                "rid": f.get("rule_id", "unknown"),
                "sev": f.get("severity", "low"),
                "cat": "audit",
                "cn": claim_number,
                "ft": file_type,
            })
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def get_analytics():
    """Return aggregate analytics."""
    db = Session()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM analytics_logs")).scalar() or 0
        by_rule = db.execute(text(
            "SELECT rule_id, severity, COUNT(*) as cnt FROM analytics_logs "
            "GROUP BY rule_id, severity ORDER BY cnt DESC LIMIT 20"
        )).fetchall()
        by_severity = db.execute(text(
            "SELECT severity, COUNT(*) as cnt FROM analytics_logs GROUP BY severity"
        )).fetchall()
        
        return {
            "total_findings": total,
            "by_rule": [{"rule_id": r[0], "severity": r[1], "count": r[2]} for r in by_rule],
            "by_severity": [{"severity": r[0], "count": r[1]} for r in by_severity],
        }
    finally:
        db.close()
