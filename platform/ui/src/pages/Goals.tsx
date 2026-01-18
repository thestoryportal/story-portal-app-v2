import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'
import { Target, Plus, TrendingUp, CheckCircle2, Clock, AlertCircle } from 'lucide-react'
import type { Goal } from '../types'

export default function Goals() {
  const queryClient = useQueryClient()
  const [showCreateGoalForm, setShowCreateGoalForm] = useState(false)
  const [showCreatePlanForm, setShowCreatePlanForm] = useState(false)
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null)

  const [newGoal, setNewGoal] = useState<Partial<Goal>>({
    description: '',
    priority: 'medium',
    constraints: {},
    context: {},
  })

  const [newPlan, setNewPlan] = useState({
    goal_id: '',
    strategy: '',
    tasks: [] as Array<{ task_id: string; description: string; dependencies: string[] }>,
  })

  const { data: goals, isLoading: goalsLoading } = useQuery({
    queryKey: ['goals'],
    queryFn: () => apiClient.listGoals(),
    refetchInterval: 5000,
  })

  const { data: plans, isLoading: plansLoading } = useQuery({
    queryKey: ['plans', selectedGoal],
    queryFn: () => (selectedGoal ? apiClient.listPlans(selectedGoal) : Promise.resolve([])),
    enabled: !!selectedGoal,
  })

  const createGoalMutation = useMutation({
    mutationFn: (goal: Partial<Goal>) => apiClient.createGoal(goal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] })
      setShowCreateGoalForm(false)
      setNewGoal({
        description: '',
        priority: 'medium',
        constraints: {},
        context: {},
      })
    },
  })

  const createPlanMutation = useMutation({
    mutationFn: (plan: { goal_id: string; strategy: string; tasks: any[] }) =>
      apiClient.createPlan(plan.goal_id, plan.strategy, plan.tasks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans'] })
      setShowCreatePlanForm(false)
      setNewPlan({
        goal_id: '',
        strategy: '',
        tasks: [],
      })
    },
  })

  const handleCreateGoal = () => {
    createGoalMutation.mutate(newGoal)
  }

  const handleCreatePlan = () => {
    if (!newPlan.goal_id || !newPlan.strategy) {
      alert('Please provide goal ID and strategy')
      return
    }
    createPlanMutation.mutate(newPlan)
  }

  const addTask = () => {
    const taskId = prompt('Enter task ID:')
    const description = prompt('Enter task description:')
    if (taskId && description) {
      setNewPlan((prev) => ({
        ...prev,
        tasks: [
          ...prev.tasks,
          {
            task_id: taskId,
            description: description,
            dependencies: [],
          },
        ],
      }))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />
      case 'in_progress':
        return <TrendingUp className="w-5 h-5 text-blue-600" />
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-600" />
      default:
        return <Clock className="w-5 h-5 text-yellow-600" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-green-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Goals & Plans</h1>
          <p className="text-gray-500 mt-1">
            Manage strategic goals and execution plans ({goals?.length || 0} goals)
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowCreateGoalForm(true)}
            className="btn btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create Goal</span>
          </button>
          <button
            onClick={() => setShowCreatePlanForm(true)}
            className="btn btn-secondary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create Plan</span>
          </button>
        </div>
      </div>

      {/* Create Goal Form */}
      {showCreateGoalForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Goal</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Goal Description
              </label>
              <textarea
                value={newGoal.description}
                onChange={(e) => setNewGoal({ ...newGoal, description: e.target.value })}
                placeholder="Describe the goal to achieve"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={newGoal.priority}
                onChange={(e) =>
                  setNewGoal({ ...newGoal, priority: e.target.value as Goal['priority'] })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleCreateGoal}
                disabled={createGoalMutation.isPending}
                className="btn btn-primary"
              >
                {createGoalMutation.isPending ? 'Creating...' : 'Create Goal'}
              </button>
              <button
                onClick={() => setShowCreateGoalForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>

            {createGoalMutation.isError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  {(createGoalMutation.error as Error).message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Plan Form */}
      {showCreatePlanForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Plan</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Goal ID</label>
              <input
                type="text"
                value={newPlan.goal_id}
                onChange={(e) => setNewPlan({ ...newPlan, goal_id: e.target.value })}
                placeholder="Enter goal ID to plan for"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Strategy</label>
              <textarea
                value={newPlan.strategy}
                onChange={(e) => setNewPlan({ ...newPlan, strategy: e.target.value })}
                placeholder="Describe the strategy to achieve the goal"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tasks</label>
              <div className="space-y-2 mb-2">
                {newPlan.tasks.map((task, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">{task.task_id}</p>
                      <p className="text-xs text-gray-600">{task.description}</p>
                    </div>
                    <button
                      onClick={() =>
                        setNewPlan({
                          ...newPlan,
                          tasks: newPlan.tasks.filter((_, i) => i !== idx),
                        })
                      }
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <button onClick={addTask} className="btn btn-secondary text-sm">
                + Add Task
              </button>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleCreatePlan}
                disabled={createPlanMutation.isPending}
                className="btn btn-primary"
              >
                {createPlanMutation.isPending ? 'Creating...' : 'Create Plan'}
              </button>
              <button
                onClick={() => setShowCreatePlanForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>

            {createPlanMutation.isError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  {(createPlanMutation.error as Error).message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Goals Grid */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Active Goals ({goals?.length || 0})
        </h2>
        {goalsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading goals...</div>
        ) : goals && goals.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {goals.map((goal) => (
              <div
                key={goal.goal_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
                onClick={() => setSelectedGoal(goal.goal_id)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Target className="w-5 h-5 text-primary-600" />
                    <span
                      className={`text-xs font-medium uppercase ${getPriorityColor(
                        goal.priority
                      )}`}
                    >
                      {goal.priority}
                    </span>
                  </div>
                  <span
                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                      goal.status
                    )}`}
                  >
                    {goal.status}
                  </span>
                </div>
                <p className="text-sm text-gray-900 line-clamp-3">{goal.description}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <span>ID: {goal.goal_id.slice(0, 8)}...</span>
                  <span>{new Date(goal.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No goals found. Create your first goal to get started.
          </div>
        )}
      </div>

      {/* Plans for Selected Goal */}
      {selectedGoal && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Plans for Goal: {selectedGoal.slice(0, 12)}...
          </h2>
          {plansLoading ? (
            <div className="text-center py-8 text-gray-500">Loading plans...</div>
          ) : plans && plans.length > 0 ? (
            <div className="space-y-4">
              {plans.map((plan) => (
                <div key={plan.plan_id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">
                        Plan: {plan.plan_id.slice(0, 12)}...
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">{plan.strategy}</p>
                    </div>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                        plan.status
                      )}`}
                    >
                      {plan.status}
                    </span>
                  </div>

                  {/* Task List */}
                  <div className="mt-4">
                    <h4 className="text-xs font-medium text-gray-700 mb-2">
                      Tasks ({plan.tasks?.length || 0})
                    </h4>
                    <div className="space-y-2">
                      {plan.tasks?.slice(0, 5).map((task: any) => (
                        <div
                          key={task.task_id}
                          className="flex items-center space-x-3 p-2 bg-gray-50 rounded"
                        >
                          {getStatusIcon(task.status || 'pending')}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-900">
                              {task.task_id}
                            </p>
                            <p className="text-xs text-gray-500 truncate">
                              {task.description}
                            </p>
                          </div>
                        </div>
                      ))}
                      {plan.tasks && plan.tasks.length > 5 && (
                        <p className="text-xs text-gray-500 text-center">
                          +{plan.tasks.length - 5} more tasks
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
                    <span>Created: {new Date(plan.created_at).toLocaleString()}</span>
                    {plan.completed_at && (
                      <span>Completed: {new Date(plan.completed_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No plans found for this goal. Create a plan to define execution strategy.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
