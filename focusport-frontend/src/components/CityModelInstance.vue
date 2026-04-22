<script setup>
import { computed, ref, shallowRef, watch } from 'vue'
import { useGLTF } from '@tresjs/cientos'
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'

const props = defineProps({
  item: { type: Object, required: true },
  isSelected: { type: Boolean, default: false },
  ghost: { type: Boolean, default: false },
  showSelectionIndicator: { type: Boolean, default: false },
  targetFootprint: { type: Number, default: 0 }
})

const DEFAULT_MODEL_SIZE = 2.2
const modelLoaded = ref(false)
const modelError = ref(false)
const loadedScene = shallowRef(null)
const loadSequence = ref(0)

const modelPath = computed(() => props.item?.model_path || props.item?.modelPath || '')
const itemCode = computed(() => props.item?.item_code || props.item?.itemCode || '')

const placementType = computed(() => {
  if (props.item?.placement_type || props.item?.placementType) return props.item.placement_type || props.item.placementType
  if (props.item?.category === 'structures') return 'building'
  if (['plants', 'trees'].includes(props.item?.category)) return 'greenery'
  return 'building'
})

const previewAccent = computed(() => (placementType.value === 'greenery' ? '#53f0b0' : '#73e0ff'))
const isCityAsset = computed(() => /\/city-assets\//i.test(String(modelPath.value || '')))
const isSkyscraper = computed(() => {
  return /skyscraper/i.test(String(itemCode.value || '')) || /skyscraper/i.test(String(modelPath.value || ''))
})

const fallbackColor = computed(() => {
  if (props.ghost) return previewAccent.value
  if (props.isSelected) return '#ffd700'
  return placementType.value === 'greenery' ? '#4ade80' : '#8bc34a'
})

const fallbackEmissive = computed(() => {
  if (props.ghost) return previewAccent.value
  return props.isSelected ? '#ff9800' : '#000000'
})

const ghostOpacity = computed(() => (props.ghost ? 0.58 : 1))

const cloneMaterialForDisplay = (material, forcedMap = null) => {
  const next = material?.clone ? material.clone() : material
  if (!next) return next

  const activeMap = forcedMap || next.map || null
  if (activeMap) {
    activeMap.colorSpace = THREE.SRGBColorSpace
    activeMap.needsUpdate = true
  }

  if (isCityAsset.value) {
    const cityMaterial = new THREE.MeshBasicMaterial({
      map: activeMap,
      color: new THREE.Color('#ffffff'),
      transparent: props.ghost || Boolean(next.transparent),
      opacity: props.ghost ? 0.58 : (typeof next.opacity === 'number' ? next.opacity : 1),
      side: THREE.DoubleSide
    })
    if (props.ghost) {
      cityMaterial.color = new THREE.Color(previewAccent.value)
      cityMaterial.opacity = 0.52
      cityMaterial.depthWrite = false
      cityMaterial.depthTest = false
    }
    cityMaterial.needsUpdate = true
    return cityMaterial
  }

  if (!props.ghost) {
    if (next.map) {
      next.map.colorSpace = THREE.SRGBColorSpace
      next.map.needsUpdate = true
    }
    if ('color' in next && next.color?.isColor && next.color.equals(new THREE.Color(0x000000))) {
      next.color = new THREE.Color('#ffffff')
    }
    if ('emissive' in next && next.emissive?.isColor) {
      next.emissive = next.emissive.clone().lerp(new THREE.Color('#ffffff'), 0.12)
      next.emissiveIntensity = Math.max(next.emissiveIntensity || 0, 0.08)
    }
    next.needsUpdate = true
    return next
  }

  next.transparent = true
  next.opacity = Math.min(typeof next.opacity === 'number' ? next.opacity : 1, 0.58)
  if ('depthWrite' in next) next.depthWrite = false
  if ('depthTest' in next) next.depthTest = false
  if ('emissive' in next && next.emissive?.isColor) {
    next.emissive = new THREE.Color(previewAccent.value)
    next.emissiveIntensity = Math.max(next.emissiveIntensity || 0, 0.18)
  }
  if ('color' in next && next.color?.isColor) {
    next.color = next.color.clone().lerp(new THREE.Color(previewAccent.value), 0.22)
  }
  return next
}

const resolvePreferredModelPath = (modelPath) => {
  const sourcePath = String(modelPath || '')
  if (!sourcePath) return ''
  if (/\/city-assets\//i.test(sourcePath) && /\/Models\/OBJ format\//i.test(sourcePath) && /\.obj$/i.test(sourcePath)) {
    return sourcePath
      .replace('/Models/OBJ format/', '/Models/GLB format/')
      .replace(/\.obj$/i, '.glb')
  }
  return sourcePath
}

const resolveCityTexturePath = (modelPath) => {
  const sourcePath = String(modelPath || '')
  if (!/\/city-assets\//i.test(sourcePath)) return ''
  if (/\/Models\/GLB format\//i.test(sourcePath)) {
    return sourcePath.replace(/\/[^/]+$/i, '/Textures/colormap.png')
  }
  if (/\/Models\/OBJ format\//i.test(sourcePath)) {
    return sourcePath.replace(/\/OBJ format\/[^/]+$/i, '/Textures/colormap.png')
  }
  return ''
}

const normalizeModelToGround = (object) => {
  const box = new THREE.Box3().setFromObject(object)
  const size = new THREE.Vector3()
  const center = new THREE.Vector3()
  box.getSize(size)
  box.getCenter(center)

  const maxSize = Math.max(size.x, size.y, size.z)
  const horizontalFootprint = Math.max(size.x, size.z)
  if (!Number.isFinite(maxSize) || maxSize <= 0) return object

  let scaleFactor = DEFAULT_MODEL_SIZE / maxSize
  if (isSkyscraper.value && Number.isFinite(horizontalFootprint) && horizontalFootprint > 0 && props.targetFootprint > 0) {
    scaleFactor = props.targetFootprint / horizontalFootprint
  }

  object.scale.multiplyScalar(scaleFactor)

  const normalizedBox = new THREE.Box3().setFromObject(object)
  const normalizedCenter = new THREE.Vector3()
  normalizedBox.getCenter(normalizedCenter)
  object.position.x -= normalizedCenter.x
  object.position.y -= normalizedBox.min.y
  object.position.z -= normalizedCenter.z
  return object
}

const styleObjectForDisplay = (object, sharedTexture = null) => {
  object.traverse((child) => {
    if (!child?.isMesh) return
    child.frustumCulled = false
    child.castShadow = !props.ghost
    child.receiveShadow = !props.ghost
    if (props.ghost) child.renderOrder = 30
    if (!child.material) return
    child.material = Array.isArray(child.material)
      ? child.material.map((material) => cloneMaterialForDisplay(material, sharedTexture))
      : cloneMaterialForDisplay(child.material, sharedTexture)
  })
  return object
}

const loadObjModel = async (encodedPath) => {
  const lastSlash = encodedPath.lastIndexOf('/')
  const basePath = lastSlash >= 0 ? encodedPath.slice(0, lastSlash + 1) : ''
  const resourceRoot = basePath.replace(/\/OBJ%20format\/$/i, '/')
  const objFile = lastSlash >= 0 ? encodedPath.slice(lastSlash + 1) : encodedPath
  const mtlFile = objFile.replace(/\.obj$/i, '.mtl')

  const objLoader = new OBJLoader()
  if (basePath) objLoader.setPath(basePath)

  try {
    const mtlLoader = new MTLLoader()
    if (basePath) {
      mtlLoader.setPath(basePath)
      mtlLoader.setResourcePath(resourceRoot || basePath)
    }
    const materials = await mtlLoader.loadAsync(mtlFile)
    materials.preload()
    objLoader.setMaterials(materials)
  } catch (error) {
    console.warn(`Failed to load MTL: ${mtlFile}`, error)
  }

  return objLoader.loadAsync(objFile)
}

const loadModel = async () => {
  const currentSequence = ++loadSequence.value
  modelLoaded.value = false
  modelError.value = false
  loadedScene.value = null

  if (!modelPath.value) {
    modelError.value = true
    return
  }

  const preferredPath = resolvePreferredModelPath(modelPath.value)
  let sharedTexture = null

  try {
    const encodedPreferredPath = preferredPath.replace(/ /g, '%20')
    const texturePath = resolveCityTexturePath(preferredPath || modelPath.value)
    if (texturePath) {
      sharedTexture = await new THREE.TextureLoader().loadAsync(texturePath.replace(/ /g, '%20'))
      sharedTexture.colorSpace = THREE.SRGBColorSpace
      sharedTexture.needsUpdate = true
    }
    let sceneObject
    if (encodedPreferredPath.toLowerCase().endsWith('.obj')) {
      sceneObject = await loadObjModel(encodedPreferredPath)
    } else {
      const { scene } = await useGLTF(encodedPreferredPath)
      const gltfScene = scene?.value || scene
      if (!gltfScene) {
        throw new Error(`GLTF scene is empty: ${encodedPreferredPath}`)
      }
      sceneObject = gltfScene.clone(true)
    }

    if (currentSequence !== loadSequence.value) return

    const preparedScene = styleObjectForDisplay(normalizeModelToGround(sceneObject), sharedTexture)
    preparedScene.updateMatrixWorld(true)
    loadedScene.value = preparedScene
    modelLoaded.value = true
  } catch (error) {
    const fallbackObjPath = String(modelPath.value || '').replace(/ /g, '%20')
    if (preferredPath !== modelPath.value && /\.obj$/i.test(fallbackObjPath)) {
      try {
        const fallbackScene = await loadObjModel(fallbackObjPath)
        if (currentSequence !== loadSequence.value) return
        const preparedFallbackScene = styleObjectForDisplay(normalizeModelToGround(fallbackScene), sharedTexture)
        preparedFallbackScene.updateMatrixWorld(true)
        loadedScene.value = preparedFallbackScene
        modelLoaded.value = true
        modelError.value = false
        return
      } catch (fallbackError) {
        console.warn(`Failed to load fallback OBJ: ${modelPath.value}`, fallbackError)
      }
    }
    if (currentSequence !== loadSequence.value) return
    console.warn(`Failed to load model: ${modelPath.value}`, error)
    modelError.value = true
  }
}

watch(
  () => [modelPath.value, itemCode.value, props.targetFootprint, props.ghost],
  () => {
    loadModel()
  },
  { immediate: true }
)
</script>

<template>
  <primitive v-if="modelLoaded && loadedScene" :object="loadedScene" />

  <TresGroup v-else>
    <TresMesh>
      <TresBoxGeometry :args="ghost ? [1.05, 1.5, 1.05] : [0.8, 0.8, 0.8]" />
      <TresMeshStandardMaterial
        :color="fallbackColor"
        :emissive="fallbackEmissive"
        :emissive-intensity="ghost ? 0.45 : isSelected ? 0.3 : 0"
        :transparent="ghost"
        :opacity="ghostOpacity"
      />
    </TresMesh>
    <TresMesh :position="[0, ghost ? 0.9 : 0.6, 0]">
      <TresSphereGeometry :args="[ghost ? 0.22 : 0.15, 8, 8]" />
      <TresMeshStandardMaterial
        :color="fallbackColor"
        :emissive="fallbackEmissive"
        :emissive-intensity="ghost ? 0.35 : isSelected ? 0.18 : 0"
        :transparent="ghost"
        :opacity="ghostOpacity"
      />
    </TresMesh>
  </TresGroup>

  <TresMesh v-if="showSelectionIndicator && isSelected" :position="[0, 1.2, 0]">
    <TresConeGeometry :args="[0.2, 0.4, 4]" />
    <TresMeshStandardMaterial color="#ffd700" emissive="#ff9800" :emissive-intensity="0.5" />
  </TresMesh>
</template>
