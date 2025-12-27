SELECT
    studies.nct_id,
    studies.brief_title,
    studies.phase,
    studies.overall_status,

    -- Drugs
    COALESCE(
        json_agg(
            DISTINCT jsonb_build_object(
                'name',        interventions.name,
                'description', interventions.description
            )
        )
        FILTER (
            WHERE interventions.intervention_type IN ('DRUG', 'BIOLOGICAL')
              AND interventions.name IS NOT NULL
        ),
        '[]'
    ) AS drugs,

    -- Conditions
    COALESCE(
        json_agg(DISTINCT conditions.name)
        FILTER (
            WHERE conditions.name IS NOT NULL
        ),
        '[]'
    ) AS conditions,

    -- Sponsors (lead only)
    COALESCE(
        json_agg(
            DISTINCT jsonb_build_object(
                'name',  sponsors.name,
                'class', sponsors.agency_class
            )
        )
        FILTER (
            WHERE sponsors.lead_or_collaborator = 'lead'
              AND sponsors.name IS NOT NULL
        ),
        '[]'
    ) AS sponsors

FROM studies
LEFT JOIN interventions
       ON studies.nct_id = interventions.nct_id
LEFT JOIN conditions
       ON studies.nct_id = conditions.nct_id
LEFT JOIN sponsors
       ON studies.nct_id = sponsors.nct_id

WHERE studies.study_type = 'INTERVENTIONAL'
  AND studies.phase IN (
      'PHASE1',
      'PHASE2',
      'PHASE3',
      'PHASE4',
      'PHASE1/PHASE2',
      'PHASE2/PHASE3'
  )

GROUP BY
    studies.nct_id,
    studies.brief_title,
    studies.phase,
    studies.overall_status

LIMIT 1000;