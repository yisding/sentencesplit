# frozen_string_literal: true
#
# Batch runner for the original Ruby pragmatic_segmenter, the reference
# implementation that pySBD (and, transitively, sentencesplit) is a port of.
#
# Protocol: read a single JSON object from stdin of the form
#   {"language": "en", "texts": ["...", "..."]}
# and write a single JSON object to stdout of the form
#   {"sentences": [["sent", ...], ...]}
# One subprocess call segments a whole batch, amortizing interpreter startup.

require "json"
require "pragmatic_segmenter"

payload = JSON.parse($stdin.read)
language = payload["language"] || "en"
texts = payload["texts"] || []

results = texts.map do |text|
  begin
    seg = PragmaticSegmenter::Segmenter.new(text: text, language: language, clean: false)
    seg.segment.map { |s| s.strip }.reject(&:empty?)
  rescue StandardError
    # Fall back to English if the language is unsupported by the gem.
    seg = PragmaticSegmenter::Segmenter.new(text: text, clean: false)
    seg.segment.map { |s| s.strip }.reject(&:empty?)
  end
end

$stdout.write(JSON.generate({ "sentences" => results }))
