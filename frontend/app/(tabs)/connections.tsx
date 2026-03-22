import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  Modal,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useAuth } from '../../contexts/AuthContext';
import { useRouter } from 'expo-router';
import axios from 'axios';
import Constants from 'expo-constants';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

interface Connection {
  id: string;
  user: {
    id: string;
    name: string;
    phone_number: string;
  };
  location: {
    latitude: number;
    longitude: number;
    timestamp: string;
    address?: string;
    street?: string;
    city?: string;
    country?: string;
  } | null;
}

interface PendingRequest {
  id: string;
  requester: {
    id: string;
    name: string;
    phone_number: string;
  };
  created_at: string;
}

export default function ConnectionsScreen() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [pendingRequests, setPendingRequests] = useState<PendingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchConnections();
    fetchPendingRequests();
  }, []);

  const fetchConnections = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/connections`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setConnections(response.data);
    } catch (error) {
      console.error('Error fetching connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingRequests = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/connections/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPendingRequests(response.data);
    } catch (error) {
      console.error('Error fetching pending requests:', error);
    }
  };

  const sendConnectionRequest = async () => {
    if (!phoneNumber.trim()) {
      Alert.alert('Error', 'Please enter a phone number');
      return;
    }

    setSending(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/connections/request`,
        { target_phone: phoneNumber },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      Alert.alert('Success', 'Connection request sent!');
      setPhoneNumber('');
      setModalVisible(false);
      fetchConnections();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send request');
    } finally {
      setSending(false);
    }
  };

  const acceptRequest = async (requestId: string) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/connections/${requestId}/accept`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      Alert.alert('Success', 'Connection accepted!');
      fetchConnections();
      fetchPendingRequests();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to accept request');
    }
  };

  const rejectRequest = async (requestId: string) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/connections/${requestId}/reject`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      Alert.alert('Success', 'Connection rejected');
      fetchPendingRequests();
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject request');
    }
  };

  const renderConnection = ({ item }: { item: Connection }) => (
    <View style={styles.connectionCard}>
      <View style={styles.avatarContainer}>
        <Ionicons name="person" size={32} color="#007AFF" />
      </View>
      <View style={styles.connectionInfo}>
        <Text style={styles.connectionName}>{item.user.name}</Text>
        <Text style={styles.connectionPhone}>{item.user.phone_number}</Text>
        {item.location && (
          <>
            {item.location.street && (
              <Text style={styles.addressText}>
                📍 {item.location.street}
                {item.location.city && `, ${item.location.city}`}
              </Text>
            )}
            <Text style={styles.locationText}>
              Last seen: {new Date(item.location.timestamp).toLocaleString()}
            </Text>
          </>
        )}
      </View>
      <View style={styles.connectionActions}>
        {Platform.OS !== 'web' ? (
          <TouchableOpacity
            style={styles.callButton}
            onPress={() =>
              router.push({
                pathname: `/call/${item.user.id}`,
                params: {
                  channelName: `call_${user?.id}_${item.user.id}`,
                  targetUserId: item.user.id,
                  targetUserName: item.user.name,
                },
              })
            }
          >
            <Ionicons name="videocam" size={24} color="#fff" />
          </TouchableOpacity>
        ) : (
          <View style={[styles.callButton, styles.callButtonDisabled]}>
            <Ionicons name="videocam-off" size={24} color="#666" />
          </View>
        )}
        <Ionicons name="checkmark-circle" size={24} color="#34C759" />
      </View>
    </View>
  );

  const renderPendingRequest = ({ item }: { item: PendingRequest }) => (
    <View style={styles.requestCard}>
      <View style={styles.avatarContainer}>
        <Ionicons name="person-add" size={32} color="#FF9500" />
      </View>
      <View style={styles.requestInfo}>
        <Text style={styles.requestName}>{item.requester.name}</Text>
        <Text style={styles.requestPhone}>{item.requester.phone_number}</Text>
      </View>
      <View style={styles.requestActions}>
        <TouchableOpacity
          style={styles.acceptButton}
          onPress={() => acceptRequest(item.id)}
        >
          <Ionicons name="checkmark" size={20} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.rejectButton}
          onPress={() => rejectRequest(item.id)}
        >
          <Ionicons name="close" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Connections</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      {pendingRequests.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pending Requests ({pendingRequests.length})</Text>
          <FlatList
            data={pendingRequests}
            renderItem={renderPendingRequest}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
          />
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>My Connections ({connections.length})</Text>
        {connections.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={64} color="#666" />
            <Text style={styles.emptyText}>No connections yet</Text>
            <Text style={styles.emptySubtext}>Add someone to start tracking</Text>
          </View>
        ) : (
          <FlatList
            data={connections}
            renderItem={renderConnection}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
          />
        )}
      </View>

      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Connection</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={28} color="#fff" />
              </TouchableOpacity>
            </View>

            <View style={styles.inputContainer}>
              <Ionicons name="call" size={20} color="#666" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter phone number"
                placeholderTextColor="#666"
                value={phoneNumber}
                onChangeText={setPhoneNumber}
                keyboardType="phone-pad"
              />
            </View>

            <TouchableOpacity
              style={[styles.sendButton, sending && styles.sendButtonDisabled]}
              onPress={sendConnectionRequest}
              disabled={sending}
            >
              <Text style={styles.sendButtonText}>
                {sending ? 'Sending...' : 'Send Request'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2C2C2E',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  addButton: {
    backgroundColor: '#007AFF',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  section: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  listContent: {
    paddingHorizontal: 16,
  },
  connectionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1C1C1E',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  requestCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1C1C1E',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    marginHorizontal: 16,
  },
  avatarContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2C2C2E',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  connectionInfo: {
    flex: 1,
  },
  connectionName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  connectionPhone: {
    fontSize: 14,
    color: '#999',
    marginBottom: 4,
  },
  addressText: {
    fontSize: 13,
    color: '#007AFF',
    marginBottom: 4,
  },
  locationText: {
    fontSize: 12,
    color: '#666',
  },
  connectionActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  callButton: {
    backgroundColor: '#007AFF',
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  callButtonDisabled: {
    backgroundColor: '#2C2C2E',
  },
  requestInfo: {
    flex: 1,
  },
  requestName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  requestPhone: {
    fontSize: 14,
    color: '#999',
  },
  requestActions: {
    flexDirection: 'row',
    gap: 8,
  },
  acceptButton: {
    backgroundColor: '#34C759',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rejectButton: {
    backgroundColor: '#FF3B30',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyContainer: {
    flex: 1,
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
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1C1C1E',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2C2C2E',
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    height: 56,
    color: '#fff',
    fontSize: 16,
  },
  sendButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});
