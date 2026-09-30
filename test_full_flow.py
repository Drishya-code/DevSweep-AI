import sys
sys.path.insert(0, 'C:/Users/Drishya/DevSweepAI/backend')
from cleanup.engine import CleanupEngine, PlanGenerator, CleanupItem, CleanupPlan, RiskLevel, ActionType
from cleanup.routes import _cleanup_plans
from scanner.detector import analyze_project
from pathlib import Path

# Test the full flow via the engine
demo_path = Path('C:/Users/Drishya/DevSweepAI/demo-project')

# 1. Analyze project
analysis = analyze_project(demo_path)
print(f'Project type: {analysis.project_type}')
print(f'Framework: {analysis.framework}')
print(f'Candidates: {len(analysis.cleanup_candidates)}')

# 2. Generate plan
generator = PlanGenerator(demo_path)
plan = generator.generate_plan([
    {
        "path": c.path,
        "risk": c.risk.value,
        "reason": c.reason,
        "size_bytes": c.size_bytes,
    }
    for c in analysis.cleanup_candidates
])
print(f'Plan items: {len(plan.items)}')
for item in plan.items:
    print(f'  {item.path} - {item.risk.value} - {item.action.value}')

# 3. Execute plan
engine = CleanupEngine(demo_path)
result = engine.execute_plan(plan, approved=True)
print(f'Result: success={result.success}, deleted={result.items_deleted}, failed={result.items_failed}, bytes={result.bytes_freed}')
print(f'Errors: {result.errors}')