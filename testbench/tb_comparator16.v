`timescale 1ns/1ps
module tb_comparator16;
    reg clk=0;
    always #5 clk=~clk;
    reg [15:0] a=0,b=0;
    reg [15:0] prev_a=0,prev_b=0;
    wire greater, equal;
    integer cycle=0, k;
    reg exp_gt, exp_eq;
    comparator16 dut(.clk(clk), .a(a), .b(b), .greater(greater), .equal(equal));
    always @(posedge clk) begin
        if (cycle>0) begin
            exp_gt = prev_a > prev_b;
            exp_eq = prev_a == prev_b;
            #1;
            if (greater !== exp_gt || equal !== exp_eq) $fatal(1,"comparator mismatch cycle %0d",cycle);
        end
        prev_a=a; prev_b=b; cycle=cycle+1;
    end
    initial begin
        for(k=0;k<250;k=k+1) begin
            @(negedge clk);
            a=$random; b=(k%3==0)?a:$random;
        end
        @(negedge clk);
        $display("PASS: comparator16 %0d vectors",cycle-1);
        $finish;
    end
endmodule
