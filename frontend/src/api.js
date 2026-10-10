// Cliente de la API. Nunca lanza: devuelve { ok, data } o { ok: false, error: { error, code } }.

const BASE = '/api';

async function request(path, init) {
  try {
    const res = await fetch(BASE + path, init);
    let body = null;
    try {
      body = await res.json();
    } catch {
      /* respuesta sin JSON */
    }
    if (res.ok) return { ok: true, data: body };
    return {
      ok: false,
      status: res.status,
      error: body && body.error ? body : { error: `Error ${res.status}`, code: 'http_error' },
    };
  } catch {
    return { ok: false, status: 0, error: { error: 'No se pudo conectar con el servidor.', code: 'network' } };
  }
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  regions: () => request('/regions'),
  layers: (rid) => request(`/regions/${rid}/layers`),
  pois: (rid) => request(`/regions/${rid}/pois`),
  presets: (rid) => request(`/regions/${rid}/route/presets`),
  cell: (rid, lat, lon) => request(`/regions/${rid}/cell?lat=${lat}&lon=${lon}`),
  route: (rid, body) => post(`/regions/${rid}/route`, body),
  missions: (rid, body) => post(`/regions/${rid}/missions`, body),
  select: (rid, resultId, weights) => post(`/regions/${rid}/missions/${resultId}/select`, weights),
};
