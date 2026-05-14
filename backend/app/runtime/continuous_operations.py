from __future__ import annotations
from datetime import datetime
from .models import RuntimeOperation, RuntimeCycle, OperationType, OperationStatus, RuntimeMode
from .runtime_memory import RuntimeMemory
from .runtime_limits import RuntimeLimits


class ContinuousOperations:
    def __init__(self):
        self._memory = RuntimeMemory()
        self._limits = RuntimeLimits()
        self._cycle_counter = 0

    def _next_cycle_number(self) -> int:
        cycles = self._memory.get_cycles(limit=1)
        if cycles:
            return cycles[-1].get("cycle_number", 0) + 1
        return 1

    def prepare_cycle(self, project: str, mode: RuntimeMode = RuntimeMode.manual) -> RuntimeCycle:
        cycle = RuntimeCycle(
            cycle_number=self._next_cycle_number(),
            project=project,
            mode=mode,
            status=OperationStatus.queued,
        )
        self._memory.save_cycle(cycle)
        return cycle

    def execute_operation(self, operation: RuntimeOperation) -> RuntimeOperation:
        can_run, reason = self._limits.can_execute(operation.trust_score, operation.cost_estimate)
        if not can_run:
            operation.status = OperationStatus.blocked
            operation.error = reason
            self._memory.save_operation(operation)
            return operation

        operation.status = OperationStatus.running
        operation.started_at = datetime.utcnow()
        self._memory.save_operation(operation)

        try:
            result = self._run_operation(operation)
            operation.status = OperationStatus.completed if result["success"] else OperationStatus.failed
            operation.result_summary = result.get("summary", "")
            operation.actual_cost = result.get("cost", 0.0)
            if not result["success"]:
                operation.error = result.get("error", "unknown")
        except Exception as e:
            operation.status = OperationStatus.failed
            operation.error = str(e)

        operation.completed_at = datetime.utcnow()
        self._memory.save_operation(operation)
        self._limits.record_operation(operation.id, operation.actual_cost)
        return operation

    def _run_operation(self, operation: RuntimeOperation) -> dict:
        op_type = operation.operation_type
        if op_type == OperationType.health_check or op_type == "health_check":
            return {"success": True, "summary": f"Health check for {operation.project} completed", "cost": 0.0}
        if op_type == OperationType.analysis or op_type == "analysis":
            return {"success": True, "summary": f"Analysis of {operation.project} completed", "cost": 0.001}
        if op_type == OperationType.planning or op_type == "planning":
            return {"success": True, "summary": f"Planning cycle for {operation.project} completed", "cost": 0.002}
        return {"success": True, "summary": f"Operation {op_type} for {operation.project} completed", "cost": 0.0}

    def run_cycle(self, project: str, operation_types: list[str], trust_score: float = 0.5, mode: RuntimeMode = RuntimeMode.manual) -> RuntimeCycle:
        cycle = self.prepare_cycle(project, mode)
        cycle.operations_planned = len(operation_types)
        cycle.status = OperationStatus.running
        self._memory.save_cycle(cycle)

        for op_type_str in operation_types:
            try:
                op_type = OperationType(op_type_str)
            except ValueError:
                op_type = OperationType.health_check

            op = RuntimeOperation(
                operation_type=op_type,
                project=project,
                trust_score=trust_score,
            )
            op = self.execute_operation(op)

            if op.status == OperationStatus.completed:
                cycle.operations_completed += 1
            elif op.status == OperationStatus.failed:
                cycle.operations_failed += 1
            else:
                cycle.operations_skipped += 1

            cycle.total_cost += op.actual_cost

        cycle.status = OperationStatus.completed if cycle.operations_failed == 0 else OperationStatus.failed
        cycle.completed_at = datetime.utcnow()
        self._memory.save_cycle(cycle)
        return cycle
