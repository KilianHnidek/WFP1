import { Component } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { saveAs } from 'file-saver';
import { DomSanitizer, SafeResourceUrl  } from '@angular/platform-browser';

@Component({
  selector: 'app-analysis',
  templateUrl: './analysis.component.html',
  styleUrls: ['./analysis.component.scss']
})
export class AnalysisComponent {
  apiUrl = '/backend/xlsx';
  apiUrl2 = '/predictor/predict';


constructor(private http: HttpClient, private sanitizer: DomSanitizer) { }
  figures: SafeResourceUrl[] = [];

  analysis(): void {
    this.http.get(this.apiUrl2).subscribe(
      (response: any) => {
        this.figures = response.figures.map((figure: string) => this.sanitizer.bypassSecurityTrustHtml(figure));
      },
      (error: any) => {
        console.error('Error:', error);
      }
    );
  }



  download(): void {
  const headers = new HttpHeaders().set('Content-Type', 'application/json');
  this.http.get(this.apiUrl, { responseType: 'blob', headers: headers })
    .subscribe(
      (response: Blob) => {
        saveAs(response, `file.xlsx`);
      },
      (error: any) => {
        console.error('Error:', error);
      }
    );
  }
}
