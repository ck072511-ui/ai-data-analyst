import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  TextField,
  IconButton,
  Typography,
  CircularProgress,
  Avatar,
  Chip,
  Alert,
  Button,
  Snackbar,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  History as HistoryIcon,
  Download as DownloadIcon,
  BarChart as ChartIcon,
  TableChart as TableIcon,
  Code as CodeIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { useNotifications } from '../contexts/NotificationContext';
import { chatService } from '../services/chatService';
import { analyticsService } from '../services/analyticsService';
import MessageComponent from '../components/MessageComponent';
import ChartVisualization from '../components/ChartVisualization';
import { debounce } from 'lodash';

const ChatInterface = () => {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { user } = useAuth();
  const { showNotification } = useNotifications();
  const queryClient = useQueryClient();

  // Load chat history
  const { data: chatHistory, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['chatHistory', user?.id],
    queryFn: () => chatService.getHistory(),
    enabled: !!user,
    refetchOnWindowFocus: false,
  });

  // Initialize chat session
  useEffect(() => {
    if (chatHistory?.session) {
      setCurrentSession(chatHistory.session);
      setMessages(chatHistory.messages || []);
    }
  }, [chatHistory]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Track user activity
  useEffect(() => {
    const trackActivity = debounce(() => {
      analyticsService.trackEvent('chat_active', { user_id: user?.id });
    }, 5000);

    const interval = setInterval(trackActivity, 30000);
    return () => clearInterval(interval);
  }, [user]);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (question) => {
      setIsProcessing(true);
      return await chatService.sendMessage(question, currentSession?.id);
    },
    onSuccess: (response) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', ...response },
      ]);
      
      // Track successful query
      analyticsService.trackEvent('query_success', {
        question: response.question,
        row_count: response.data?.length || 0,
        execution_time: response.metadata?.execution_time,
      });
      
      // Invalidate cache
      queryClient.invalidateQueries(['chatHistory']);
      
      // Show notification for large results
      if (response.data?.length > 1000) {
        showNotification('Large result set returned', 'info');
      }
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          error: true,
          content: 'Sorry, I encountered an error. Please try again.',
        },
      ]);
      
      analyticsService.trackEvent('query_error', {
        error: error.message,
        question: message,
      });
      
      showNotification('Failed to process your query', 'error');
    },
    onSettled: () => {
      setIsProcessing(false);
    },
  });

  const handleSendMessage = useCallback(async () => {
    if (!message.trim() || isProcessing) return;

    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setMessage('');
    inputRef.current?.focus();

    await sendMessageMutation.mutateAsync(message);
  }, [message, isProcessing, sendMessageMutation]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleExport = async (format = 'pdf') => {
    try {
      const data = await chatService.exportChat(messages, format);
      const blob = new Blob([data], { 
        type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat_export_${Date.now()}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      analyticsService.trackEvent('export_chat', { format });
      showNotification('Export started successfully', 'success');
    } catch (error) {
      showNotification('Failed to export chat', 'error');
    }
  };

  const handleCopySQL = (sql) => {
    navigator.clipboard.writeText(sql);
    showNotification('SQL copied to clipboard', 'success');
  };

  return (
    <Container maxWidth="lg" sx={{ height: 'calc(100vh - 100px)', py: 3 }}>
      <Paper 
        elevation={0}
        sx={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box sx={{ 
          p: 2, 
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          bgcolor: 'background.paper',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              <ChartIcon />
            </Avatar>
            <Box>
              <Typography variant="h6" fontWeight={600}>
                AI Data Analyst
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {isLoadingHistory ? 'Loading history...' : 'Ask any question about your data'}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Export PDF">
              <IconButton onClick={() => handleExport('pdf')} disabled={!messages.length}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Export Excel">
              <IconButton onClick={() => handleExport('excel')} disabled={!messages.length}>
                <TableIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="History">
              <IconButton onClick={() => navigate('/history')}>
                <HistoryIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Messages */}
        <Box sx={{ 
          flex: 1, 
          overflowY: 'auto',
          p: 3,
          bgcolor: 'background.default',
        }}>
          {messages.length === 0 ? (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
            }}>
              <ChartIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
              <Typography variant="h6" gutterBottom>
                Start a conversation
              </Typography>
              <Typography variant="body2" align="center" sx={{ maxWidth: 400 }}>
                Ask questions about your data in natural language.
                Try: "Show me total sales by region for last month"
              </Typography>
            </Box>
          ) : (
            messages.map((msg, index) => (
              <MessageComponent
                key={index}
                message={msg}
                onCopySQL={handleCopySQL}
              />
            ))
          )}
          {isProcessing && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                Analyzing your question...
              </Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input */}
        <Box sx={{ 
          p: 2, 
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask a question about your data..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isProcessing || sendMessageMutation.isLoading}
              inputRef={inputRef}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 3,
                },
              }}
            />
            <IconButton
              color="primary"
              onClick={handleSendMessage}
              disabled={!message.trim() || isProcessing || sendMessageMutation.isLoading}
              sx={{ 
                alignSelf: 'flex-end',
                bgcolor: 'primary.main',
                color: 'white',
                '&:hover': {
                  bgcolor: 'primary.dark',
                },
                '&.Mui-disabled': {
                  bgcolor: 'grey.300',
                },
                borderRadius: 3,
                p: 2,
              }}
            >
              {isProcessing || sendMessageMutation.isLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                <SendIcon />
              )}
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {messages.length} messages • Press Enter to send
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {user?.email}
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Error Snackbar */}
      <Snackbar
        open={!!sendMessageMutation.error}
        autoHideDuration={6000}
        onClose={() => sendMessageMutation.reset()}
      >
        <Alert severity="error" onClose={() => sendMessageMutation.reset()}>
          {sendMessageMutation.error?.message || 'Failed to process query'}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default ChatInterface;