// 1. Top drugs by number of trials
// Usage: :param limit => 10
// Example: :params {limit: 10}
MATCH (d:Drug)<-[:STUDIED_IN]-(t:Trial)
RETURN d.name AS drug, count(t) AS trials
ORDER BY trials DESC
LIMIT $limit;

// 2. For a given company, list associated drugs and conditions
// Usage: :param org => "Novartis"
// Example: :params {org: "Novartis"}
MATCH (o:Organization {name: $org})<-[:SPONSORED_BY]-(t:Trial)
OPTIONAL MATCH (t)-[:STUDIED_IN]->(d:Drug)
OPTIONAL MATCH (t)-[:STUDIES_CONDITION]->(c:Condition)
RETURN o.name AS organization,
       collect(DISTINCT d.name) AS drugs,
       collect(DISTINCT c.name) AS conditions;

// 3. For a given condition, show drugs being studied and trial phases
// Usage: :param cond => "Alzheimer Disease"
// Example: :params {cond: "Alzheimer Disease"}
MATCH (c:Condition {name: $cond})<-[:STUDIES_CONDITION]-(t:Trial)-[:STUDIED_IN]->(d:Drug)
RETURN d.name AS drug,
       collect(DISTINCT t.phase) AS phases,
       count(DISTINCT t) AS trial_count
ORDER BY trial_count DESC;

// 4. Route and dosage form coverage (counts)
// Shows how many STUDIED_IN relationships have route/dosage_form populated
MATCH ()-[r:STUDIED_IN]->()
RETURN
  count(r) AS total_relationships,
  count { (r.route IS NOT NULL) AND (r.route <> "Unknown") } AS with_route,
  count { (r.dosage_form IS NOT NULL) AND (r.dosage_form <> "Unknown") } AS with_dosage_form;


