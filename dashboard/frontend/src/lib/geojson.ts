// Australia state GeoJSON polygons (simplified)
export const australiaStates = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { id: "NSW1", name: "New South Wales" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [141.0, -28.0], [153.5, -28.0], [153.5, -37.5], [148.5, -37.5],
          [148.5, -34.0], [141.0, -34.0], [141.0, -28.0]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { id: "QLD1", name: "Queensland" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [138.0, -10.0], [153.5, -10.0], [153.5, -29.0], [141.0, -29.0],
          [141.0, -26.0], [138.0, -26.0], [138.0, -10.0]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { id: "SA1", name: "South Australia" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [129.0, -26.0], [141.0, -26.0], [141.0, -38.0], [140.5, -38.0],
          [129.0, -38.0], [129.0, -26.0]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { id: "TAS1", name: "Tasmania" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [144.5, -39.0], [148.5, -39.0], [148.5, -44.0], [144.5, -44.0],
          [144.5, -39.0]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { id: "VIC1", name: "Victoria" },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [141.0, -34.0], [150.0, -34.0], [150.0, -39.0], [148.5, -39.0],
          [141.0, -39.0], [141.0, -34.0]
        ]]
      }
    }
  ]
};

export const regionMeta: Record<string, { name: string; center: [number, number]; zoom: number }> = {
  NSW1: { name: "New South Wales", center: [147.0, -33.0], zoom: 6 },
  QLD1: { name: "Queensland", center: [145.0, -22.0], zoom: 5.5 },
  SA1:  { name: "South Australia", center: [135.0, -32.0], zoom: 5.5 },
  TAS1: { name: "Tasmania", center: [146.5, -41.5], zoom: 7 },
  VIC1: { name: "Victoria", center: [145.5, -37.0], zoom: 6.5 },
};