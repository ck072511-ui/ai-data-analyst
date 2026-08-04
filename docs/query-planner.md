# Distributed Query Planner Specifications

The Distributed Query Planner decomposes natural language prompts into structured multi-database execution plans.

## Planner Prompt Layout
The planner instructs the local LLM to return a valid JSON object matching the planner schema:
```json
{
  "subqueries": [
    {
      "db_connection_id": "target-connection-uuid",
      "sql": "SELECT order_id, user_id FROM orders",
      "alias": "t1"
    }
  ],
  "merge_operations": {
    "type": "join|union|union_all|single",
    "join_type": "inner|left",
    "left_table": "t1",
    "right_table": "t2",
    "left_on": "column_in_left",
    "right_on": "column_in_right",
    "projection": ["column1", "column2"]
  }
}
```

## Performance & Optimization Rules
1. **Schema Context Pruning**: Rather than passing entire database schemas, only matching schemas matching the target question keywords are passed to the planner LLM, keeping offline token contexts small and execution speeds high.
2. **Push Down Projections**: The planner enforces column selections (`SELECT columns`) on subqueries instead of broad select stars (`SELECT *`), minimizing in-memory pandas buffer footprints.
3. **Join Key Coercion**: To prevent data merge schema mismatches, join keys are coerced to String datatypes before pandas `merge` actions.
