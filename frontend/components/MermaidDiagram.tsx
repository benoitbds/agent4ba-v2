"use client";

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  code: string;
}

/**
 * Composant pour afficher un diagramme Mermaid
 *
 * @param code - Code Mermaid à rendre
 */
export default function MermaidDiagram({ code }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initialiser Mermaid avec la configuration
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'monospace',
    });

    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        // Générer un ID unique pour le diagramme
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // Rendre le diagramme
        const { svg } = await mermaid.render(id, code);

        // Insérer le SVG dans le conteneur
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }

        setError(null);
      } catch (err) {
        console.error('Error rendering Mermaid diagram:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };

    renderDiagram();
  }, [code]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4 text-sm">
        <p className="text-red-700 font-semibold mb-2">Erreur lors du rendu du diagramme</p>
        <p className="text-red-600 text-xs">{error}</p>
        <details className="mt-2">
          <summary className="cursor-pointer text-red-700 font-medium text-xs">
            Voir le code Mermaid
          </summary>
          <pre className="mt-2 p-2 bg-red-100 rounded text-xs overflow-x-auto">
            {code}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="mermaid-diagram bg-white border border-gray-200 rounded p-4 overflow-x-auto"
      style={{ minHeight: '100px' }}
    />
  );
}
