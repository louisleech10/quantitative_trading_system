// frontend/src/store/searchStore.ts
// Global state management for search functionality

import { create } from 'zustand';
import { CaseData, SearchResult, SearchTemplate } from '@/lib/types';
import { apiClient } from '@/lib/api';

interface SearchState {
  // Data
  templates: SearchTemplate[];
  currentResult: SearchResult | null;
  searchHistory: SearchResult[];

  // UI State
  isLoading: boolean;
  error: string | null;
  selectedTemplate: SearchTemplate | null;

  // Actions
  loadTemplates: () => Promise<void>;
  executeSearch: (templateId: string) => Promise<void>;
  pollTaskStatus: (taskId: string) => Promise<void>;
  clearError: () => void;
  setSelectedTemplate: (template: SearchTemplate | null) => void;
  setSearchResult: (result: any) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  // Initial state
  templates: [],
  currentResult: null,
  searchHistory: [],
  isLoading: false,
  error: null,
  selectedTemplate: null,

  // Load available search templates
  loadTemplates: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiClient.getSearchTemplates();
      
      if (response.success && response.data) {
        set({ templates: response.data });
      } else {
        throw new Error(response.error?.message || 'Failed to load templates');
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Unknown error occurred' });
    } finally {
      set({ isLoading: false });
    }
  },

  // Execute search with selected template
  executeSearch: async (templateId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      // Start search task
      const response = await apiClient.executeSearch({ template_id: templateId });
      
      if (response.success && response.data) {
        const taskId = response.data.task_id;
        
        // Start polling for results
        await get().pollTaskStatus(taskId);
      } else {
        throw new Error(response.error?.message || 'Failed to start search');
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Search execution failed' });
      set({ isLoading: false });
    }
  },

  // Poll task status and update result
  pollTaskStatus: async (taskId: string) => {
    const pollInterval = 2000; // 2 seconds
    const maxAttempts = 150; // 5 minutes max
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        attempts++;
        
        const response = await apiClient.getTaskStatus(taskId);
        
        if (response.success && response.data) {
          const result = response.data;
          
          // Update current result
          set({ currentResult: result });
          
          if (result.status === 'completed') {
            // Fetch full result data
            const resultResponse = await apiClient.getTaskResult(taskId);
            
            if (resultResponse.success && resultResponse.data) {
              const fullResult = resultResponse.data;
              
              set({ 
                currentResult: fullResult,
                isLoading: false,
                searchHistory: [...get().searchHistory, fullResult]
              });
            }
            return;
          }
          
          if (result.status === 'failed') {
            throw new Error(result.error || 'Search task failed');
          }
          
          // Continue polling if still running
          if (result.status === 'running' || result.status === 'pending') {
            if (attempts < maxAttempts) {
              setTimeout(poll, pollInterval);
            } else {
              throw new Error('Search timeout - task took too long to complete');
            }
          }
        } else {
          throw new Error(response.error?.message || 'Failed to get task status');
        }
      } catch (error) {
        set({ 
          error: error instanceof Error ? error.message : 'Polling failed',
          isLoading: false 
        });
      }
    };

    // Start polling
    poll();
  },

  // Clear error state
  clearError: () => set({ error: null }),

  // Set selected template
  setSelectedTemplate: (template: SearchTemplate | null) => {
    set({ selectedTemplate: template });
  },

  // Set search result
  setSearchResult: (result: any) => {
    set({ currentResult: result });
  },

  // Set loading state
  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  // Set error state
  setError: (error: string | null) => {
    set({ error });
  },
}));