import { circlePolygon, clearGeoJSON, setGeoJSON, stopMarker } from './map.js';

/** Color por riesgo: la capa 'mission-line' usa propiedad `risk` = fracción de metros en terreno de riesgo. */
export function legFeatures(mission) {
  return mission.legs
    .filter((leg) => leg.coordinates && leg.coordinates.length >= 2)
    .map((leg) => ({
      type: 'Feature',
      properties: { risk: leg.distance_m > 0 ? leg.risk_m / leg.distance_m : 0, from: leg.from, to: leg.to },
      geometry: { type: 'LineString', coordinates: leg.coordinates },
    }));
}

export function createMissionLayer(map) {
  let markers = [];

  function clearMarkers() {
    markers.forEach((m) => m.remove());
    markers = [];
  }

  return {
    draw(mission, poisById) {
      clearMarkers();
      setGeoJSON(map, 'mission-legs', { type: 'FeatureCollection', features: legFeatures(mission) });
      mission.sequence.forEach((id, i) => {
        const poi = poisById[id];
        if (poi) markers.push(stopMarker(map, i + 1, poi.coordinates, `${i + 1}. ${poi.name}`));
      });
    },
    drawWalkback(habitat, radiusM) {
      setGeoJSON(map, 'walkback', circlePolygon(habitat.lat, habitat.lon, radiusM));
    },
    clear() {
      clearMarkers();
      clearGeoJSON(map, 'mission-legs');
      clearGeoJSON(map, 'walkback');
    },
  };
}
