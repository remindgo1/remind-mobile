const appEnvironment = process.env.APP_ENV || 'dev';

module.exports = ({ config }) => ({
  ...config,
  name: `ReMind ${appEnvironment.toUpperCase()}`,
  ios: {
    ...config.ios,
    bundleIdentifier: `com.remind.care.${appEnvironment}`,
  },
  android: {
    ...config.android,
    package: `com.remind.care.${appEnvironment}`,
  },
  extra: {
    ...config.extra,
    appEnvironment,
    eas: {
      ...config.extra?.eas,
      projectId:
        process.env.EAS_PROJECT_ID ||
        config.extra?.eas?.projectId,
    },
  },
});