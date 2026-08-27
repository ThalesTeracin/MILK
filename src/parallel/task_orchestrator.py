from review.self_review import SelfReview
from parallel.parallel_manager import ParallelManager

class TaskOrchestrator:
    def __init__(self, ai=None, max_workers=3):
        self.review = SelfReview(ai=ai)
        self.parallel = ParallelManager(max_workers=max_workers)

    def execute_and_review(self, task_name, jobs):
        execution = self.parallel.run_jobs(jobs)

        evidence = []
        for item in execution:
            if item.get("ok"):
                evidence.append({"ok": True, "job": item["name"], "result": item.get("result")})
            else:
                evidence.append({"ok": False, "job": item["name"], "error": item.get("error")})

        decision = self.review.final_decision(task_name, evidence)

        return {
            "task": task_name,
            "execution": execution,
            "review": decision
        }
