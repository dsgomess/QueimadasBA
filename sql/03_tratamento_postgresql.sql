create or replace view vw_queimadas_tratadas as 
select 
	datahora,
	extract(year from datahora) as ano,
	extract(month from datahora) as mes,
	extract(day from datahora) as dia,
	satelite,
	pais,
	estado,
	municipio,
	bioma,
	case when diasemchuva = -999 then null else diasemchuva end as diasemchuva,
	case when precipitacao = -999 then null else precipitacao end as precipitacao,
	case when riscofogo = -999 then null else riscofogo end as riscofogo,
	case when frp = -999 then null else frp end as frp,
	latitude,
	longitude
from vw_queimadas_unificadas;