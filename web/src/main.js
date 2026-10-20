import { mount } from 'svelte';
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/newsreader/400.css';
import '@fontsource/newsreader/500.css';
import '@fontsource/newsreader/400-italic.css';
import '@fontsource/newsreader/500-italic.css';
import './app.css';
import App from './App.svelte';

mount(App, { target: document.getElementById('app') });
