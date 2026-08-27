from src.memory.long_memory import LongMemory
db=LongMemory()
print("=== MILK - MEMÓRIA LONGA ===")
print("Status:", db.stats())
print("\nProjetos:")
for p in db.list_projects(limit=20):
    print("-", p)
print("\nDecisões:")
for d in db.latest_decisions(limit=20):
    print("-", d)
db.close()
