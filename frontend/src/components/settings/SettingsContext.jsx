import { createContext, useContext } from 'react';

// Shares editor-wide metadata (the personality trait definitions and the
// person generator) with deep field components without prop-drilling. The
// PersonalitySliders editor reads the trait defs from here; EntityList uses
// generatePerson to mint a persona when a new person is added.
const SettingsMetaContext = createContext({ traitDefs: [], generatePerson: null });

export const SettingsMetaProvider = SettingsMetaContext.Provider;

export function useSettingsMeta() {
  return useContext(SettingsMetaContext);
}
