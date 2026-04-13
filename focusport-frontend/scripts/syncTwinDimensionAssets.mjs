import { promises as fs } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const frontendRoot = path.resolve(__dirname, '..')
const publicRoot = path.join(frontendRoot, 'public')
const modelsRoot = path.join(publicRoot, 'models')
const gaiaRoot = path.join(publicRoot, 'assets', '2d', 'gaia')
const manifestPath = path.join(publicRoot, 'assets', '2d', 'manifest.json')
const constantsPath = path.join(frontendRoot, 'src', 'constants', 'assets.js')

const downloadsRoot = process.env.GAIA_SOURCE_ROOT || 'C:\\Users\\86153\\Downloads\\2D'

const sourcePacks = [
  {
    key: 'buildings',
    label: 'Kenney Isometric Buildings',
    sourceDir: path.join(downloadsRoot, 'kenney_isometric-buildings'),
    category: 'structures',
    subcategory: 'buildings'
  },
  {
    key: 'city',
    label: 'Kenney Isometric City',
    sourceDir: path.join(downloadsRoot, 'kenney_isometric-city'),
    category: 'structures',
    subcategory: 'buildings'
  },
  {
    key: 'vehicles',
    label: 'Kenney Isometric Vehicles',
    sourceDir: path.join(downloadsRoot, 'kenney_isometric-vehicles'),
    category: 'structures',
    subcategory: 'vehicles'
  }
]

const TILE_WIDTH = 96
const TILE_HEIGHT = 48
const GRID_COLS = 20
const GRID_ROWS = 20

const VEHICLE_FILE_PREFERENCE = [
  /_NEU\.png$/i,
  /_NE\.png$/i,
  /_N\.png$/i,
  /_E\.png$/i,
  /_000\.png$/i
]

const VEHICLE_ANGLE_SUFFIX = /_(?:NED|NEU|NWD|NWU|SED|SEU|SWD|SWU|NE|NW|SE|SW|N|S|E|W|\d{3})$/i
const SELLABLE_3D_PATTERN = /(building|skyscraper|planter|tree|flower|road|bench|statue|tower|sign)/i

function toPosix(value) {
  return value.split(path.sep).join('/')
}

function slugify(value) {
  return value
    .replace(/\.[^.]+$/, '')
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
    .toLowerCase()
}

function titleCaseFromSlug(value) {
  return value
    .split('-')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function escapeJsString(value) {
  return String(value)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
}

async function ensureDirectory(targetPath) {
  await fs.mkdir(targetPath, { recursive: true })
}

async function resetDirectory(targetPath) {
  const resolved = path.resolve(targetPath)
  const allowedRoot = path.resolve(path.join(publicRoot, 'assets', '2d', 'gaia'))
  if (resolved !== allowedRoot) {
    throw new Error(`Refusing to clear unexpected directory: ${resolved}`)
  }
  await fs.rm(resolved, { recursive: true, force: true })
  await ensureDirectory(resolved)
}

async function collectFiles(rootDir, matcher) {
  const collected = []

  async function walk(currentDir) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true })
    for (const entry of entries) {
      const absolutePath = path.join(currentDir, entry.name)
      if (entry.isDirectory()) {
        await walk(absolutePath)
        continue
      }
      if (matcher(absolutePath)) {
        collected.push(absolutePath)
      }
    }
  }

  await walk(rootDir)
  return collected
}

function pickPreferredVehicleFile(files) {
  const byPreference = [...files].sort((left, right) => left.localeCompare(right))
  for (const pattern of VEHICLE_FILE_PREFERENCE) {
    const match = byPreference.find((filePath) => pattern.test(filePath))
    if (match) return match
  }
  return byPreference[0]
}

function normalizeVehicleStem(filePath) {
  return path.basename(filePath, '.png').replace(VEHICLE_ANGLE_SUFFIX, '')
}

function buildVehicleLabel(groupKey, filePath) {
  const directoryLabel = path.basename(groupKey)
  const normalizedStem = normalizeVehicleStem(filePath)
  const rawLabel = slugify(directoryLabel === 'PNG' ? normalizedStem : `${directoryLabel}-${normalizedStem}`)
  return titleCaseFromSlug(rawLabel)
}

function rarityForIndex(index) {
  if (index % 17 === 0) return 'legendary'
  if (index % 9 === 0) return 'epic'
  if (index % 4 === 0) return 'rare'
  return 'common'
}

function priceForAsset(packKey, subcategory, index) {
  const base = subcategory === 'vehicles' ? 80 : 140
  const packBonus = packKey === 'buildings' ? 60 : packKey === 'city' ? 40 : 20
  return base + packBonus + (index % 11) * 15
}

function footprintForAsset(packKey, relativePath) {
  const relative = toPosix(relativePath).toLowerCase()
  if (packKey === 'vehicles') {
    return { width: 1, height: 1 }
  }
  if (relative.includes('/details/')) {
    return { width: 1, height: 1 }
  }
  if (relative.includes('road') || relative.includes('tile')) {
    return { width: 1, height: 1 }
  }
  return { width: 2, height: 2 }
}

async function syncGaiaAssets() {
  await resetDirectory(gaiaRoot)

  const copiedAssets = []

  for (const pack of sourcePacks) {
    await ensureDirectory(path.join(gaiaRoot, pack.key))
    const allPngs = await collectFiles(pack.sourceDir, (absolutePath) => (
      absolutePath.toLowerCase().endsWith('.png') &&
      path.basename(absolutePath).toLowerCase() !== 'preview.png'
    ))

    let selectedFiles = allPngs
    if (pack.key === 'vehicles') {
      const groups = new Map()
      for (const filePath of allPngs) {
        const relativeDir = path.dirname(path.relative(pack.sourceDir, filePath))
        const groupKey = toPosix(relativeDir === '.' ? path.basename(filePath, '.png') : relativeDir)
        const existing = groups.get(groupKey) || []
        existing.push(filePath)
        groups.set(groupKey, existing)
      }
      selectedFiles = [...groups.values()].map(pickPreferredVehicleFile)
    }

    const packAssets = []

    for (const [index, absolutePath] of selectedFiles.sort((left, right) => left.localeCompare(right)).entries()) {
      const relativePath = path.relative(pack.sourceDir, absolutePath)
      const destinationName = `${slugify(pack.key === 'vehicles' ? buildVehicleLabel(path.dirname(relativePath), absolutePath) : path.basename(relativePath, '.png'))}.png`
      const destinationPath = path.join(gaiaRoot, pack.key, destinationName)
      await ensureDirectory(path.dirname(destinationPath))
      await fs.copyFile(absolutePath, destinationPath)

      const footprint = footprintForAsset(pack.key, relativePath)
      const label = pack.key === 'vehicles'
        ? buildVehicleLabel(path.dirname(relativePath), absolutePath)
        : titleCaseFromSlug(slugify(path.basename(relativePath, '.png')))
      const itemCode = `gaia_${pack.key}_${slugify(path.basename(destinationName, '.png'))}`
      const publicPath = `/assets/2d/gaia/${pack.key}/${destinationName}`

      packAssets.push({
        item_code: itemCode,
        name: label,
        name_cn: label,
        description: `${pack.label} asset imported from local library.`,
        category: pack.category,
        subcategory: pack.subcategory,
        dimension: '2D',
        preview_path: publicPath,
        sprite_path: publicPath,
        grid_width: footprint.width,
        grid_height: footprint.height,
        price_coins: priceForAsset(pack.key, pack.subcategory, index),
        price_sunshine: rarityForIndex(index) === 'legendary' ? 4 : 0,
        rarity: rarityForIndex(index),
        icon: pack.subcategory === 'vehicles' ? 'vehicle' : 'building',
        sort_order: copiedAssets.length + index + 1,
        tags: `gaia,kenney,${pack.key},${pack.subcategory}`,
        pack: pack.key,
        asset_path: publicPath,
        css_preset: 'hologram-blue'
      })
    }

    copiedAssets.push(...packAssets)
  }

  const manifest = {
    version: 2,
    theme: 'gaia-simulator',
    grid: {
      cols: GRID_COLS,
      rows: GRID_ROWS,
      tile_width: TILE_WIDTH,
      tile_height: TILE_HEIGHT
    },
    items: copiedAssets
  }

  await ensureDirectory(path.dirname(manifestPath))
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
  return copiedAssets
}

async function syncPhysicalAssets() {
  const glbFiles = await collectFiles(modelsRoot, (absolutePath) => absolutePath.toLowerCase().endsWith('.glb'))
  return glbFiles
    .sort((left, right) => left.localeCompare(right))
    .map((absolutePath) => {
      const relativePath = toPosix(path.relative(publicRoot, absolutePath))
      const fileName = path.basename(relativePath, '.glb')
      const relativeParts = relativePath.split('/')
      const sourceCategory = relativeParts.length > 1 ? slugify(relativeParts[relativeParts.length - 2]) : 'models'
      return {
        id: `physical_${slugify(relativePath)}`,
        name: titleCaseFromSlug(slugify(fileName)),
        assetPath: `/${relativePath}`,
        sourceCategory,
        sellable: SELLABLE_3D_PATTERN.test(relativePath),
        dimension: '3D'
      }
    })
}

async function writeAssetConstants(gaiaAssets, physicalAssets) {
  const gaiaLiteral = gaiaAssets
    .map((asset) => `  {
    assetId: '${escapeJsString(asset.item_code)}',
    itemCode: '${escapeJsString(asset.item_code)}',
    name: '${escapeJsString(asset.name)}',
    nameCn: '${escapeJsString(asset.name_cn)}',
    assetPath: '${escapeJsString(asset.asset_path)}',
    previewPath: '${escapeJsString(asset.preview_path)}',
    spritePath: '${escapeJsString(asset.sprite_path)}',
    pack: '${escapeJsString(asset.pack)}',
    category: '${escapeJsString(asset.category)}',
    subcategory: '${escapeJsString(asset.subcategory)}',
    dimension: 'GAIA',
    footprint: { width: ${asset.grid_width}, height: ${asset.grid_height} },
    cssPreset: 'hologram-blue',
    priceCoins: ${asset.price_coins},
    priceSunshine: ${asset.price_sunshine},
    rarity: '${escapeJsString(asset.rarity)}'
  }`)
    .join(',\n')

  const physicalLiteral = physicalAssets
    .map((asset) => `  {
    assetId: '${escapeJsString(asset.id)}',
    name: '${escapeJsString(asset.name)}',
    assetPath: '${escapeJsString(asset.assetPath)}',
    sourceCategory: '${escapeJsString(asset.sourceCategory)}',
    sellable: ${asset.sellable ? 'true' : 'false'},
    dimension: 'PHYSICAL'
  }`)
    .join(',\n')

  const output = `// Auto-generated by scripts/syncTwinDimensionAssets.mjs
export const PHYSICAL_BAY_ASSETS = [
${physicalLiteral}
]

export const GAIA_SIMULATOR_ASSETS = [
${gaiaLiteral}
]

export const PHYSICAL_BAY_ASSET_MAP = new Map(
  PHYSICAL_BAY_ASSETS.map((asset) => [asset.assetPath, asset])
)

export const GAIA_SIMULATOR_ASSET_MAP = new Map(
  GAIA_SIMULATOR_ASSETS.flatMap((asset) => [
    [asset.itemCode, asset],
    [asset.assetPath, asset]
  ])
)
`

  await ensureDirectory(path.dirname(constantsPath))
  await fs.writeFile(constantsPath, output, 'utf8')
}

async function main() {
  console.log(`[sync] reading local GAIA assets from ${downloadsRoot}`)
  const gaiaAssets = await syncGaiaAssets()
  const physicalAssets = await syncPhysicalAssets()
  await writeAssetConstants(gaiaAssets, physicalAssets)

  console.log(`[sync] wrote ${gaiaAssets.length} GAIA assets`)
  console.log(`[sync] wrote ${physicalAssets.length} PHYSICAL assets`)
  console.log(`[sync] manifest: ${manifestPath}`)
  console.log(`[sync] constants: ${constantsPath}`)
}

main().catch((error) => {
  console.error('[sync] twin dimension asset sync failed')
  console.error(error)
  process.exitCode = 1
})
