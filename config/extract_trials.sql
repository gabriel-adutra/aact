SELECT 
    s.nct_id, 
    s.brief_title, 
    s.phase, 
    s.overall_status,
    -- Agrupamos as intervenções (drogas) em uma lista JSON
    COALESCE(
        json_agg(DISTINCT jsonb_build_object('name', i.name, 'description', i.description)) 
        FILTER (WHERE i.intervention_type IN ('DRUG', 'BIOLOGICAL') AND i.name IS NOT NULL), 
        '[]'
    ) as drugs,
    -- Agrupamos condições
    COALESCE(
        json_agg(DISTINCT c.name) 
        FILTER (WHERE c.name IS NOT NULL), 
        '[]'
    ) as conditions,
    -- Agrupamos patrocinadores
    COALESCE(
        json_agg(DISTINCT jsonb_build_object('name', sp.name, 'class', sp.agency_class)) 
        FILTER (WHERE sp.lead_or_collaborator = 'lead' AND sp.name IS NOT NULL), 
        '[]'
    ) as sponsors
FROM studies s
LEFT JOIN interventions i ON s.nct_id = i.nct_id
LEFT JOIN conditions c ON s.nct_id = c.nct_id
LEFT JOIN sponsors sp ON s.nct_id = sp.nct_id
WHERE 
    s.study_type = 'INTERVENTIONAL'
    -- Filtro de fases normalizado conforme verificação no banco
    AND s.phase IN ('PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'PHASE1/PHASE2', 'PHASE2/PHASE3')
GROUP BY s.nct_id, s.brief_title, s.phase, s.overall_status
LIMIT 1000;

