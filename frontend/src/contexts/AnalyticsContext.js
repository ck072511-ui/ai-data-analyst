import React, { createContext, useContext, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

const AnalyticsContext = createContext();

// Simple analytics service
const analyticsService = {
  trackEvent: (eventName, properties = {}) => {
    // In production, send to Google Analytics, Mixpanel, etc.
    console.log(`[Analytics] ${eventName}:`, properties);
    
    // Send to backend
    try {
      fetch(`${API_BASE_URL}/analytics/track`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          event: eventName,
          properties,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {
        // Silent fail for analytics
      });
    } catch (error) {
      // Silent fail for analytics
    }
  },
  
  trackPageView: (page) => {
    analyticsService.trackEvent('page_view', { page });
  },
  
  trackError: (error, context = {}) => {
    analyticsService.trackEvent('error', { error: error.message, ...context });
  }
};

export const AnalyticsProvider = ({ children }) => {
  // Track page views
  useEffect(() => {
    // Page view tracking
    const currentPath = window.location.pathname;
    analyticsService.trackPageView(currentPath);
    
    // Track user session
    analyticsService.trackEvent('session_start', {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    });
  }, []);

  return (
    <AnalyticsContext.Provider value={analyticsService}>
      {children}
    </AnalyticsContext.Provider>
  );
};

export const useAnalytics = () => {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error('useAnalytics must be used within an AnalyticsProvider');
  }
  return context;
};
