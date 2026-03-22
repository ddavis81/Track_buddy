import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface User {
  id: string;
  phone_number: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (phone_number: string, password: string) => Promise<void>;
  register: (phone_number: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const notificationListener = useRef<any>();
  const responseListener = useRef<any>();

  useEffect(() => {
    loadStoredAuth();
    setupNotifications();
    
    return () => {
      if (notificationListener.current) {
        Notifications.removeNotificationSubscription(notificationListener.current);
      }
      if (responseListener.current) {
        Notifications.removeNotificationSubscription(responseListener.current);
      }
    };
  }, []);

  useEffect(() => {
    if (token) {
      registerForPushNotifications();
    }
  }, [token]);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('auth_token');
      const storedUser = await AsyncStorage.getItem('user');
      
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Error loading stored auth:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (phone_number: string, password: string) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/auth/login`, {
        phone_number,
        password,
      });

      const { access_token, user: userData } = response.data;
      
      await AsyncStorage.setItem('auth_token', access_token);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      
      setToken(access_token);
      setUser(userData);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  };

  const register = async (phone_number: string, password: string, name: string) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/auth/register`, {
        phone_number,
        password,
        name,
      });

      const { access_token, user: userData } = response.data;
      
      await AsyncStorage.setItem('auth_token', access_token);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      
      setToken(access_token);
      setUser(userData);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
  };

  const logout = async () => {
    await AsyncStorage.removeItem('auth_token');
    await AsyncStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const setupNotifications = () => {
    // Configure notification handling
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: true,
      }),
    });

    // Listen for notifications received while app is foregrounded
    notificationListener.current = Notifications.addNotificationReceivedListener(notification => {
      console.log('Notification received:', notification);
    });

    // Listen for user tapping on notification
    responseListener.current = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('Notification tapped:', response);
      const data = response.notification.request.content.data;
      if (data.type === 'sos_alert') {
        // Handle SOS alert tap - could navigate to map or show alert details
        console.log('SOS Alert tapped:', data);
      }
    });
  };

  const registerForPushNotifications = async () => {
    if (Platform.OS === 'web') {
      return; // Push notifications don't work on web
    }

    try {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;

      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }

      if (finalStatus !== 'granted') {
        console.log('Failed to get push token for push notification!');
        return;
      }

      const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId || 'your-project-id',
      });

      const pushToken = tokenData.data;
      console.log('Push token:', pushToken);

      // Register push token with backend
      try {
        await axios.post(
          `${BACKEND_URL}/api/push-token`,
          { expo_push_token: pushToken },
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        console.log('Push token registered with backend');
      } catch (error) {
        console.error('Error registering push token:', error);
      }

      // Set up notification channel for Android
      if (Platform.OS === 'android') {
        Notifications.setNotificationChannelAsync('emergency', {
          name: 'Emergency Alerts',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#FF0000',
          sound: 'default',
        });
      }
    } catch (error) {
      console.error('Error setting up push notifications:', error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!token && !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
