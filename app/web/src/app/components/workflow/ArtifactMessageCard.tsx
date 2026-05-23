import { Download, Eye, FileText, ListChecks, Presentation } from "lucide-react";

import type { ApiArtifact } from "../../types/api";
import type { ArtifactChatMessage } from "../../types/chat";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

const iconMap: Record<string, React.ElementType> = {
  ppt: Presentation,
  todo: ListChecks,
  report: FileText,
  file: FileText,
  html_report: FileText,
};

type ArtifactMessageCardProps = {
  message: ArtifactChatMessage;
  onOpenArtifact?: (artifact: ApiArtifact) => void;
};

export function ArtifactMessageCard({ message, onOpenArtifact }: ArtifactMessageCardProps) {
  return (
    <div className="space-y-3">
      <div className="text-sm font-medium text-gray-800">{message.title}</div>
      <div className="grid gap-3 md:grid-cols-2">
        {message.artifacts.map((artifact) => {
          const Icon = iconMap[artifact.type] ?? FileText;

          return (
            <Card key={artifact.id} className="gap-3 rounded-[20px] border-gray-200 shadow-sm">
              <CardHeader className="flex flex-row items-start gap-3 px-4 pt-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-[#1a73e8]">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-sm font-medium leading-snug text-gray-800">{artifact.title}</CardTitle>
                  <p className="mt-1 text-xs text-gray-500">{artifact.createdAt ?? "刚刚"}{artifact.size ? ` · ${artifact.size}` : ""}</p>
                </div>
              </CardHeader>
              <CardContent className="flex gap-2 px-4 pb-4 pt-0">
                <Button type="button" variant="outline" className="flex-1 rounded-xl" onClick={() => onOpenArtifact?.(artifact)}>
                  <Eye className="h-4 w-4" />
                  预览
                </Button>
                <Button type="button" className="flex-1 rounded-xl bg-[#1a73e8] hover:bg-blue-700" asChild={Boolean(artifact.url)}>
                  {artifact.url ? (
                    <a href={`${artifact.url}?download=true`} download target="_blank" rel="noreferrer">
                      <Download className="h-4 w-4" />
                      下载
                    </a>
                  ) : (
                    <span>
                      <Download className="h-4 w-4" />
                      下载
                    </span>
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
