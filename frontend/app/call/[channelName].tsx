import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import {
  createAgoraRtcEngine,
  ChannelProfileType,
  ClientRoleType,
  isAgoraAvailable,
} from '../../components/AgoraEngine';
import type { IRtcEngine } from '../../components/AgoraEngine';
import axios from 'axios';
import Constants from 'expo-constants';
import { useAuth } from '../../contexts/AuthContext';

const BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

export default function VideoCallScreen() {
  const { channelName, targetUserId, targetUserName } = useLocalSearchParams<{
    channelName: string;
    targetUserId: string;
    targetUserName: string;
  }>();
  const { token: authToken } = useAuth();
  const router = useRouter();

  const [joined, setJoined] = useState(false);
  const [remoteUid, setRemoteUid] = useState<number | null>(null);
  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(true);
  const [loading, setLoading] = useState(true);
  const [speakerOn, setSpeakerOn] = useState(true);

  const agoraEngineRef = useRef<IRtcEngine | null>(null);
  const [appId, setAppId] = useState('');
  const [agoraToken, setAgoraToken] = useState('');
  const [uid, setUid] = useState(0);

  useEffect(() => {
    initializeCall();
    return () => {
      leaveCall();
    };
  }, []);

  const initializeCall = async () => {
    try {
      // Check if Agora is available on this platform
      if (!isAgoraAvailable) {
        Alert.alert(
          'Video Calls Not Available',
          'Video calling is only available on mobile devices (iOS/Android)',
          [{ text: 'OK', onPress: () => router.back() }]
        );
        return;
      }

      // Get Agora token from backend
      const response = await axios.post(
        `${BACKEND_URL}/api/agora/token`,
        { channel_name: channelName, uid: 0 },
        { headers: { Authorization: `Bearer ${authToken}` } }
      );

      const { token, app_id, uid: generatedUid } = response.data;
      setAppId(app_id);
      setAgoraToken(token);
      setUid(generatedUid);

      // Initialize Agora engine
      const engine = createAgoraRtcEngine();
      agoraEngineRef.current = engine;

      engine.initialize({ appId: app_id });

      // Register event handlers
      engine.registerEventHandler({
        onJoinChannelSuccess: (connection, elapsed) => {
          console.log('Joined channel successfully');
          setJoined(true);
          setLoading(false);
        },
        onUserJoined: (connection, remoteUid, elapsed) => {
          console.log('Remote user joined:', remoteUid);
          setRemoteUid(remoteUid);
        },
        onUserOffline: (connection, remoteUid, reason) => {
          console.log('Remote user left:', remoteUid);
          setRemoteUid(null);
        },
        onError: (err, msg) => {
          console.error('Agora error:', err, msg);
        },
      });

      // Enable video
      engine.enableVideo();
      engine.enableAudio();

      // Set channel profile
      engine.setChannelProfile(ChannelProfileType.ChannelProfileCommunication);
      engine.setClientRole(ClientRoleType.ClientRoleBroadcaster);

      // Start preview
      engine.startPreview();

      // Join channel
      engine.joinChannel(token, channelName || 'default', generatedUid, {
        clientRoleType: ClientRoleType.ClientRoleBroadcaster,
      });
    } catch (error: any) {
      console.error('Failed to initialize call:', error);
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start call');
      setLoading(false);
      router.back();
    }
  };

  const leaveCall = async () => {
    try {
      if (agoraEngineRef.current) {
        await agoraEngineRef.current.leaveChannel();
        agoraEngineRef.current.release();
      }
    } catch (error) {
      console.error('Error leaving call:', error);
    }
    router.back();
  };

  const toggleMic = () => {
    if (agoraEngineRef.current) {
      agoraEngineRef.current.enableLocalAudio(!micOn);
      setMicOn(!micOn);
    }
  };

  const toggleCamera = () => {
    if (agoraEngineRef.current) {
      agoraEngineRef.current.enableLocalVideo(!cameraOn);
      setCameraOn(!cameraOn);
    }
  };

  const switchCamera = () => {
    if (agoraEngineRef.current) {
      agoraEngineRef.current.switchCamera();
    }
  };

  const toggleSpeaker = () => {
    if (agoraEngineRef.current) {
      agoraEngineRef.current.setEnableSpeakerphone(!speakerOn);
      setSpeakerOn(!speakerOn);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Connecting to call...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Video Views */}
      <View style={styles.videoContainer}>
        {/* Remote Video (Full screen) */}
        {remoteUid ? (
          <View style={styles.remoteVideo}>
            <Text style={styles.remoteText}>{targetUserName || 'Remote User'}</Text>
          </View>
        ) : (
          <View style={styles.waitingContainer}>
            <Ionicons name="person-outline" size={64} color="#666" />
            <Text style={styles.waitingText}>Waiting for {targetUserName} to join...</Text>
          </View>
        )}

        {/* Local Video (Picture in Picture) */}
        <View style={styles.localVideo}>
          <Text style={styles.localText}>You</Text>
        </View>
      </View>

      {/* Call Info */}
      <View style={styles.infoBar}>
        <Text style={styles.channelText}>Call with {targetUserName}</Text>
        <Text style={styles.statusText}>{joined ? 'Connected' : 'Connecting...'}</Text>
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.controlButton, !micOn && styles.controlButtonOff]}
          onPress={toggleMic}
        >
          <Ionicons name={micOn ? 'mic' : 'mic-off'} size={28} color="#fff" />
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.controlButton, !cameraOn && styles.controlButtonOff]}
          onPress={toggleCamera}
        >
          <Ionicons name={cameraOn ? 'videocam' : 'videocam-off'} size={28} color="#fff" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.controlButton} onPress={switchCamera}>
          <Ionicons name="camera-reverse" size={28} color="#fff" />
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.controlButton, !speakerOn && styles.controlButtonOff]}
          onPress={toggleSpeaker}
        >
          <Ionicons name={speakerOn ? 'volume-high' : 'volume-mute'} size={28} color="#fff" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.endCallButton} onPress={leaveCall}>
          <Ionicons name="call" size={32} color="#fff" />
        </TouchableOpacity>
      </View>
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
  loadingText: {
    color: '#fff',
    marginTop: 16,
    fontSize: 16,
  },
  videoContainer: {
    flex: 1,
    position: 'relative',
  },
  remoteVideo: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  remoteText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  localVideo: {
    position: 'absolute',
    top: 48,
    right: 16,
    width: 120,
    height: 160,
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  localText: {
    color: '#fff',
    fontSize: 14,
  },
  waitingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1a1a1a',
  },
  waitingText: {
    color: '#999',
    fontSize: 16,
    marginTop: 16,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  infoBar: {
    padding: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    alignItems: 'center',
  },
  channelText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  statusText: {
    color: '#34C759',
    fontSize: 14,
    marginTop: 4,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
  },
  controlButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2C2C2E',
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlButtonOff: {
    backgroundColor: '#FF3B30',
  },
  endCallButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#FF3B30',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
