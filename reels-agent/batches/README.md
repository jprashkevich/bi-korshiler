# Партии

Каждая партия — папка `batches/<имя>/`:

```
batch.json   — хуки, оформление, футажи, описания, кодовые слова (пишет агент)
NOTES.md     — гипотеза партии и что проверяем
out/         — готовые mp4 + captions/*.txt (создаётся рендером, не коммитится)
```

Команды:
```
node scripts/new-batch.mjs                 # новая папка с заготовкой
node scripts/validate-batch.mjs batches/X  # проверить без рендера
node scripts/render-batch.mjs batches/X    # собрать все mp4
node scripts/render-batch.mjs batches/X --stills   # быстрые png-превью
node scripts/render-batch.mjs batches/X --only id1,id2
```

`batches/example/` — эталон формата со всеми пресетами.
