import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	integrations: [
		starlight({
			title: 'GFS - Replicas by Geography',
			description: 'Documentation for Geography-aware GFS Implementation',
			social: {
				github: 'https://github.com/yourusername/gfs-replicas-by-geography',
			},
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', link: '/' },
						{ label: 'Installation', link: '/guides/installation' },
						{ label: 'Quick Start', link: '/guides/quickstart' },
					],
				},
				{
					label: 'Core Components',
					items: [
						{ label: 'Master Server', link: '/components/master' },
						{ label: 'Chunk Server', link: '/components/chunk-server' },
						{ label: 'Client', link: '/components/client' },
						{ label: 'File Manager', link: '/components/file-manager' },
						{ label: 'Chunk', link: '/components/chunk' },
						{ label: 'Utils', link: '/components/utils' },
					],
				},
				{
					label: 'Features',
					items: [
						{ label: 'Location-Based Replication', link: '/features/location-replication' },
						{ label: 'Space Management', link: '/features/space-management' },
						{ label: 'Network Visualization', link: '/features/network-visualization' },
					],
				},
			],
		}),
	],
});
