import {
  useAIPlanning,
  rewriteToActionableTitle,
  type AITaskStep,
  type DecomposeStyle,
  type GoalDecomposeInput
} from './useAIPlanning'

export type { AITaskStep, DecomposeStyle, GoalDecomposeInput }
export { rewriteToActionableTitle }

export const useGoalDecomposer = () => {
  const { generateDraftPlan } = useAIPlanning()

  const decomposeGoal = async (input: GoalDecomposeInput): Promise<AITaskStep[]> => {
    return generateDraftPlan(input)
  }

  return {
    rewriteToActionableTitle,
    decomposeGoal
  }
}

