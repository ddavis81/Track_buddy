// Platform-specific wrapper for Agora (Web platform - stub)

// Stub interfaces for web
export const createAgoraRtcEngine = () => {
  console.warn('Agora is not available on web platform');
  return null;
};

export const ChannelProfileType = {
  ChannelProfileCommunication: 0,
};

export const ClientRoleType = {
  ClientRoleBroadcaster: 1,
  ClientRoleAudience: 2,
};

export type IRtcEngine = any;

export const isAgoraAvailable = false;
