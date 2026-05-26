import sys
import json
from parser.ems_parser import EmsParser

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No ZIP archive payload supplied to binary bridge."}))
        return
        
    zip_path = sys.argv[1]
    
    try:
        from adapter import build_audit_run
        from rules_engine import RulesEngine
        parser = EmsParser()
        parsed_data = parser.analyze_zip(zip_path)
        engine = RulesEngine()
        evaluated_data = engine.evaluate_estimate(parsed_data)
        strict_result = build_audit_run(evaluated_data)
        print(json.dumps(strict_result))
    except Exception as e:
        print(json.dumps({"error": f"Internal Engine Failure: {str(e)}"}))

if __name__ == "__main__":
    main()
