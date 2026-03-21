// Platform-specific wrapper for expo-camera (Web platform - stub)
import { View } from 'react-native';

// Stub Camera for web
export const Camera = {
  requestCameraPermissionsAsync: async () => ({ status: 'denied' }),
};

export const CameraView = View;
export const isCameraAvailable = false;
