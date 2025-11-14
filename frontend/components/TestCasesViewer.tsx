"use client";

import { useTranslations } from 'next-intl';
import type { TestCase } from "@/types/events";

interface TestCasesViewerProps {
  testCases: TestCase[];
}

export default function TestCasesViewer({ testCases }: TestCasesViewerProps) {
  const t = useTranslations();

  if (!testCases || testCases.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      <h3 className="text-sm font-medium text-gray-700 mb-3">
        {t('testCases.title')}
      </h3>
      <div className="space-y-4">
        {testCases.map((testCase, index) => (
          <div
            key={index}
            className="border border-gray-300 rounded-lg p-4 bg-gray-50"
          >
            {/* Titre du cas de test */}
            <h4 className="text-base font-semibold text-gray-800 mb-3">
              {testCase.title}
            </h4>

            {/* Scénario Gherkin */}
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-600 mb-1">
                {t('testCases.scenario')}
              </p>
              <pre className="bg-white border border-gray-200 rounded p-3 text-sm text-gray-800 whitespace-pre-wrap font-mono overflow-x-auto">
{testCase.scenario}
              </pre>
            </div>

            {/* Étapes du test */}
            {testCase.steps && testCase.steps.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-600 mb-2">
                  {t('testCases.steps')}
                </p>
                <div className="overflow-x-auto">
                  <table className="min-w-full border border-gray-300 rounded-lg bg-white">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 border-b border-gray-300">
                          #
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 border-b border-gray-300">
                          {t('testCases.step')}
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 border-b border-gray-300">
                          {t('testCases.expectedResult')}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {testCase.steps.map((step, stepIndex) => (
                        <tr
                          key={stepIndex}
                          className={stepIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                        >
                          <td className="px-4 py-2 text-sm text-gray-600 border-b border-gray-200">
                            {stepIndex + 1}
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-800 border-b border-gray-200">
                            {step.step}
                          </td>
                          <td className="px-4 py-2 text-sm text-gray-800 border-b border-gray-200">
                            {step.expected_result}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
