module.exports = {
  env: {
    browser: true,
    es2021: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    '@vue/typescript/recommended',
    'prettier'
  ],
  parserOptions: {
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest', // Specify the ECMAScript version
    sourceType: 'module',
    tsconfigRootDir: __dirname,
    project: ['./tsconfig.json'], // Path to the TypeScript configuration
    extraFileExtensions: ['.vue'], // Additional file extensions
    ignorePatterns: ['.eslintrc.cjs']
  },
  plugins: ['vue', '@typescript-eslint', 'prettier', 'unused-imports', 'simple-import-sort'],
  rules: {
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/ban-ts-comment': 'warn',
    'vue/multi-word-component-names': 'warn',
    'simple-import-sort/imports': 'error',
    'simple-import-sort/exports': 'error'
  }
}
