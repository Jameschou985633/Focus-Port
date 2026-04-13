export const WORLD_NAMES = {
  currency: {
    zh: '\u7b97\u529b\u5355\u5143',
    en: 'CU'
  },
  captainLog: {
    zh: '\u8230\u957f\u6863\u6848',
    en: 'CAPTAIN LOG'
  },
  voyageRecord: {
    zh: '\u822a\u884c\u65e5\u5fd7',
    en: 'VOYAGE RECORD'
  },
  streak: {
    zh: '\u8dc3\u8fc1\u8fde\u7eed\u4f53',
    en: 'STREAK'
  },
  physical: {
    zh: '\u5b9e\u4f53\u5de5\u7a0b\u575e',
    en: 'ENGINEERING DOCK'
  },
  gaia: {
    zh: '\u76d6\u4e9a\u6f14\u7b97\u8231',
    en: 'GAIA SIMULATOR'
  },
  pulseCore: {
    zh: '\u8109\u51b2\u52a8\u529b\u6838',
    en: 'PULSE CORE'
  },
  globalSequence: {
    zh: '\u5168\u5c40\u5e8f\u5217\u6392\u7a0b',
    en: 'GLOBAL SEQUENCE'
  },
  sequenceMatrix: {
    zh: '\u903b\u8f91\u5e8f\u5217\u9635',
    en: 'LOGIC MATRIX'
  },
  masterTimeline: {
    zh: '\u4efb\u52a1\u603b\u8f74',
    en: 'MASTER TIMELINE'
  },
  tacticalAdjutant: {
    zh: '\u8230\u8f7d\u53c2\u8c0b\u7aef',
    en: 'TACTICAL ADJUTANT'
  },
  exchangePort: {
    zh: '\u7269\u8d28\u4ea4\u6362\u6e2f',
    en: 'EXCHANGE PORT'
  },
  blueprintVault: {
    zh: '\u5168\u606f\u84dd\u56fe\u5e93',
    en: 'BLUEPRINT VAULT'
  },
  protocolStation: {
    zh: '\u534f\u8bae\u7f16\u8bd1\u7ad9',
    en: 'PROTOCOL STATION'
  },
  fleetNexus: {
    zh: '\u8054\u5408\u661f\u6865\u67a2\u7ebd',
    en: 'FLEET NEXUS'
  },
  starshipArchive: {
    zh: '\u661f\u8230\u6863\u6848',
    en: 'STARSHIP ARCHIVE'
  }
}

export const composeWorldLabel = (entry) => `[ ${entry.zh} · ${entry.en} ]`
