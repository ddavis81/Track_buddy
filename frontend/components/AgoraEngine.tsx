// Platform-specific wrapper for Agora (Native platforms)
export {
  createAgoraRtcEngine,
  ChannelProfileType,
  ClientRoleType,
} from 'react-native-agora';
export type { IRtcEngine } from 'react-native-agora';

export const isAgoraAvailable = true;
