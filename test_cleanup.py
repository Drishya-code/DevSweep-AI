import sys
sys.path.insert(0, 'C:/Users/Drishya/DevSweepAI/backend')
from cleanup.engine import CleanupEngine, PlanGenerator, CleanupItem, CleanupPlan, RiskLevel, ActionType
from pathlib import Path

# Test the cleanup engine directly
demo_path = Path('C:/Users/Drishya/DevSweepAI/demo-project')
engine = CleanupEngine(demo_path)

# Create a simple plan
items = [
    CleanupItem(path='node_modules', action=ActionType.DELETE, risk=RiskLevel.SAFE, reason='test', estimated_bytes=100),
    CleanupItem(path='dist', action=ActionType.DELETE, risk=RiskLevel.SAFE, reason='test', estimated_bytes=100),
]
plan = CleanupPlan(items=items, total_safe_bytes=200)
result = engine.execute_plan(plan, approved=True)
print(f'Success: {result.success}')
print(f'Items deleted: {result.items_deleted}')
print(f'Items failed: {result.items_failed}')
print(f'Bytes freed: {result.bytes_freed}')
print(f'Errors: {result.errors}')