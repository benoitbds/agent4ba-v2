"use client";

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  code: string;
}

/**
 * Extrait le code Mermaid pur en retirant les balises markdown
 * @param rawCode - Code qui peut contenir des balises markdown ```mermaid ... ```
 * @returns Code Mermaid nettoyé
 */
function extractMermaidCode(rawCode: string): string {
  // Supprimer les balises markdown si présentes (```mermaid ou juste ```)
  const match = rawCode.match(/```(?:mermaid)?\s*([\s\S]*?)```/);
  if (match) {
    return match[1].trim();
  }
  // Si pas de balises, retourner le code tel quel (déjà nettoyé)
  return rawCode.trim();
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
        // 1. Nettoyer le code en retirant les balises markdown
        const cleanCode = extractMermaidCode(code);

        // 2. Vérifier que le code n'est pas vide après nettoyage
        if (!cleanCode) {
          setError('Le code Mermaid est vide');
          return;
        }

        // 3. Générer un ID unique pour le diagramme
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // 4. Rendre le diagramme avec le code NETTOYÉ
        const { svg } = await mermaid.render(id, cleanCode);

        // 5. Insérer le SVG dans le conteneur
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
