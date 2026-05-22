import { Send } from "lucide-react";
import type { KeyboardEvent } from "react";

import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";

type ChatComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
};

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "直接输入您的分析需求...",
}: ChatComposerProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="flex items-end gap-2 rounded-[20px] border border-gray-200 bg-white p-2 shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
      <Textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="min-h-[48px] border-none bg-transparent px-4 py-3 text-[15px] text-gray-800 shadow-none focus-visible:ring-0"
      />
      <Button
        type="button"
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="h-12 w-12 rounded-xl bg-[#1a73e8] p-0 hover:bg-blue-700"
      >
        <Send className="h-5 w-5" />
      </Button>
    </div>
  );
}
