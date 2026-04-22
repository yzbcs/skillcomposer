---
name: implement flink longest session job
description: Implement Flink job to find longest stage (max tasks) per job based on SUBMIT event gaps
---
## Steps
1. Read format.pdf and ClusterData2011_2.md to understand CSV schema with fields: timestamp, job_id, task_index, event_type, etc.
2. Implement TaskEvent class in clusterdata.datatypes with fields: timestamp (microseconds), jobId, taskIndex, eventType, machineId, priority, CPU, memory, disk, constraints
3. Implement JobEvent class in clusterdata.datatypes with fields matching job_events schema
4. In LongestSessionPerJob.main(): create ExecutionEnvironment, read gzipped task events using GzipInputFormat or HadoopInputFormat
5. Parse CSV lines into TaskEvent objects, filter only SUBMIT event types
6. Group by jobId, sort by timestamp ascending
7. For each job, identify stages: track timestamps, split when gap > 10 minutes (600,000,000 microseconds)
8. Count tasks per stage, track maximum per job
9. Output (jobId, maxStageTaskCount) tuples to local file specified by output parameter
## Constraints
- Timestamps in microseconds; 10 minutes = 600,000,000 microseconds
- Stage ends after 10 min inactivity (no SUBMIT events for that job)
- Same task resubmitted counts as separate task each SUBMIT
- Output format exactly (jobId,taskCount) one per line
- Do not change class name LongestSessionPerJob or pom.xml
## Dependencies
- Apache Flink 1.x
- Java 8+
## Examples
- Example 1: {"input": "SUBMIT events for job123: t=1000000, t=1000001, t=1000002, then gap>10min, then t=7000000000, t=7000000001", "output": "(123,3)"}
