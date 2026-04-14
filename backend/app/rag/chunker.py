from dataclasses import dataclass, field

import structlog
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = structlog.get_logger()


@dataclass
class ChunkingConfig:
	chunk_size: int = 1000
	chunk_overlap: int = 200
	separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


class DocumentChunker:
	def __init__(self, config: ChunkingConfig = None):
		self.config = config or ChunkingConfig()
		self.splitter = RecursiveCharacterTextSplitter(
			chunk_size=self.config.chunk_size,
			chunk_overlap=self.config.chunk_overlap,
			separators=self.config.separators,
			length_function=len,
		)

	async def load_document(self, file_path: str, file_type: str) -> list[Document]:
		if file_type == "pdf":
			loader = PyPDFLoader(file_path)
		elif file_type in ["docx", "doc"]:
			loader = Docx2txtLoader(file_path)
		elif file_type == "txt":
			loader = TextLoader(file_path)
		else:
			raise ValueError(f"Unsupported file type: {file_type}")

		documents = await loader.aload()
		return documents

	def chunk_documents(self, documents: list[Document], metadata: dict) -> list[Document]:
		split_chunks = self.splitter.split_documents(documents)

		chunks: list[Document] = []
		for idx, chunk in enumerate(split_chunks):
			if not chunk.page_content.strip():
				continue

			chunk.metadata.update(
				{
					"doc_id": metadata.get("doc_id"),
					"filename": metadata.get("filename"),
					"file_type": metadata.get("file_type"),
					"chunk_index": idx,
					"char_count": len(chunk.page_content),
				}
			)
			chunks.append(chunk)

		return chunks

	async def process_file(
		self,
		file_path: str,
		file_type: str,
		metadata: dict,
	) -> list[Document]:
		documents = await self.load_document(file_path=file_path, file_type=file_type)
		chunks = self.chunk_documents(documents=documents, metadata=metadata)

		logger.info(
			"File processed for chunking",
			file_path=file_path,
			file_type=file_type,
			chunk_count=len(chunks),
		)
		return chunks


document_chunker = DocumentChunker()
