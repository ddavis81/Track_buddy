import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Alert,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
  ScrollView,
} from 'react-native';
import * as Location from 'expo-location';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';
import Constants from 'expo-constants';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

// Conditionally import MapView only for native platforms
let MapView: any = null;
let Marker: any = null;
let PROVIDER_GOOGLE: any = null;

if (Platform.OS !== 'web') {
  const MapModule = require('react-native-maps');
  MapView = MapModule.default;
  Marker = MapModule.Marker;
  PROVIDER_GOOGLE = MapModule.PROVIDER_GOOGLE;
}

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface UserLocation {
  user: {
    id: string;
    name: string;
    phone_number: string;
  };
  location: {
    latitude: number;
    longitude: number;
    timestamp: string;
  } | null;
}

export default function MapScreen() {
  const { user, token } = useAuth();
  const [location, setLocation] = useState<Location.LocationObject | null>(null);
  const [connections, setConnections] = useState<UserLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [locationPermission, setLocationPermission] = useState(false);
  const mapRef = useRef<MapView>(null);
  const locationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    requestLocationPermission();
    return () => {
      if (locationIntervalRef.current) {
        clearInterval(locationIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (locationPermission) {
      startLocationTracking();
      fetchConnections();
    }
  }, [locationPermission]);

  const requestLocationPermission = async () => {
    try {
      const { status: foregroundStatus } = await Location.requestForegroundPermissionsAsync();
      
      if (foregroundStatus !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Location permission is required for tracking',
          [{ text: 'OK' }]
        );
        setLoading(false);
        return;
      }

      // Request background location permission
      if (Platform.OS !== 'web') {
        const { status: backgroundStatus } = await Location.requestBackgroundPermissionsAsync();
        if (backgroundStatus !== 'granted') {
          Alert.alert(
            'Background Location',
            'Background location permission helps track even when app is closed'
          );
        }
      }

      setLocationPermission(true);
    } catch (error) {
      console.error('Error requesting location permission:', error);
      Alert.alert('Error', 'Failed to request location permission');
      setLoading(false);
    }
  };

  const startLocationTracking = async () => {
    try {
      // Get initial location
      const currentLocation = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setLocation(currentLocation);
      await updateLocationOnServer(currentLocation.coords.latitude, currentLocation.coords.longitude);
      setLoading(false);

      // Update location every 30 seconds
      locationIntervalRef.current = setInterval(async () => {
        try {
          const newLocation = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          setLocation(newLocation);
          await updateLocationOnServer(newLocation.coords.latitude, newLocation.coords.longitude);
          fetchConnections(); // Refresh connections locations
        } catch (error) {
          console.error('Error updating location:', error);
        }
      }, 30000);
    } catch (error) {
      console.error('Error starting location tracking:', error);
      Alert.alert('Error', 'Failed to get location');
      setLoading(false);
    }
  };

  const updateLocationOnServer = async (latitude: number, longitude: number) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/locations`,
        { latitude, longitude },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
    } catch (error) {
      console.error('Error updating location on server:', error);
    }
  };

  const fetchConnections = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/connections`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setConnections(response.data);
    } catch (error) {
      console.error('Error fetching connections:', error);
    }
  };

  const centerOnMyLocation = () => {
    if (location && mapRef.current) {
      mapRef.current.animateToRegion({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        latitudeDelta: 0.01,
        longitudeDelta: 0.01,
      });
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Getting your location...</Text>
      </View>
    );
  }

  if (!locationPermission || !location) {
    return (
      <SafeAreaView style={styles.errorContainer}>
        <Ionicons name="location-outline" size={64} color="#999" />
        <Text style={styles.errorText}>Location permission required</Text>
        <TouchableOpacity style={styles.retryButton} onPress={requestLocationPermission}>
          <Text style={styles.retryButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // Web fallback - show location info instead of map
  if (Platform.OS === 'web' || !MapView) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.topBar}>
          <View style={styles.topBarContent}>
            <Text style={styles.topBarTitle}>TrackSafe</Text>
            <Text style={styles.topBarSubtitle}>
              Tracking {connections.filter((c) => c.location).length} users
            </Text>
          </View>
        </SafeAreaView>

        <ScrollView style={styles.webFallback}>
          <View style={styles.locationCard}>
            <Ionicons name="location" size={32} color="#007AFF" />
            <Text style={styles.locationTitle}>Your Location</Text>
            <Text style={styles.locationCoords}>
              Lat: {location.coords.latitude.toFixed(6)}
            </Text>
            <Text style={styles.locationCoords}>
              Lng: {location.coords.longitude.toFixed(6)}
            </Text>
          </View>

          {connections.map((conn) =>
            conn.location ? (
              <View key={conn.user.id} style={styles.userCard}>
                <View style={styles.userAvatar}>
                  <Ionicons name="person" size={24} color="#007AFF" />
                </View>
                <View style={styles.userInfo}>
                  <Text style={styles.userName}>{conn.user.name}</Text>
                  <Text style={styles.userCoords}>
                    Lat: {conn.location.latitude.toFixed(6)}, Lng: {conn.location.longitude.toFixed(6)}
                  </Text>
                  <Text style={styles.userTime}>
                    {new Date(conn.location.timestamp).toLocaleString()}
                  </Text>
                </View>
              </View>
            ) : null
          )}

          {connections.length === 0 && (
            <View style={styles.emptyState}>
              <Ionicons name="people-outline" size={64} color="#666" />
              <Text style={styles.emptyText}>No connections yet</Text>
              <Text style={styles.emptySubtext}>Add connections to see their locations</Text>
            </View>
          )}
        </ScrollView>

        <TouchableOpacity style={styles.myLocationButton} onPress={centerOnMyLocation}>
          <Ionicons name="refresh" size={24} color="#007AFF" />
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={{
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
        showsUserLocation
        showsMyLocationButton={false}
      >
        {/* Show connected users on map */}
        {connections.map((conn) =>
          conn.location ? (
            <Marker
              key={conn.user.id}
              coordinate={{
                latitude: conn.location.latitude,
                longitude: conn.location.longitude,
              }}
              title={conn.user.name}
              description={`Last updated: ${new Date(conn.location.timestamp).toLocaleTimeString()}`}
            >
              <View style={styles.markerContainer}>
                <Ionicons name="person" size={24} color="#007AFF" />
              </View>
            </Marker>
          ) : null
        )}
      </MapView>

      <SafeAreaView style={styles.topBar}>
        <View style={styles.topBarContent}>
          <Text style={styles.topBarTitle}>TrackSafe</Text>
          <Text style={styles.topBarSubtitle}>
            Tracking {connections.filter((c) => c.location).length} users
          </Text>
        </View>
      </SafeAreaView>

      <TouchableOpacity style={styles.myLocationButton} onPress={centerOnMyLocation}>
        <Ionicons name="navigate" size={24} color="#007AFF" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: '#fff',
    marginTop: 16,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    backgroundColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  errorText: {
    color: '#999',
    fontSize: 18,
    marginTop: 16,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 24,
    backgroundColor: '#007AFF',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 12,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  topBarContent: {
    padding: 16,
  },
  topBarTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  topBarSubtitle: {
    color: '#999',
    fontSize: 14,
    marginTop: 4,
  },
  myLocationButton: {
    position: 'absolute',
    bottom: 32,
    right: 16,
    backgroundColor: '#fff',
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  markerContainer: {
    backgroundColor: '#fff',
    padding: 8,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  webFallback: {
    flex: 1,
    padding: 16,
  },
  locationCard: {
    backgroundColor: '#1C1C1E',
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 16,
  },
  locationTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 12,
    marginBottom: 12,
  },
  locationCoords: {
    fontSize: 14,
    color: '#999',
    marginBottom: 4,
  },
  userCard: {
    flexDirection: 'row',
    backgroundColor: '#1C1C1E',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  userAvatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#2C2C2E',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  userCoords: {
    fontSize: 12,
    color: '#999',
    marginBottom: 2,
  },
  userTime: {
    fontSize: 11,
    color: '#666',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 18,
    color: '#999',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
});
